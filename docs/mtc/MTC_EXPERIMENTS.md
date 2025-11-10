# MTC Experiments

## Goal
Run the MoveIt Task Constructor demo `stored_state_sequence.py` for a ZA6 robot and execute the generated motion from `WALL_NEUTRAL` to `DOOR_FACING_NEUTRAL`, ideally triggered from the Motion Planning Tasks panel in RViz via the **Exec** button.

## Environment
- Workspace: `/home/pathpilot/Projects/za6_workspace`
- Script under test: `src/tormach_za_ros2_drivers/za6_moveit_config/scripts/mtc/za6_stored_state_sequence.py`
- Launch command: `ros2 launch za6_moveit_config teleop_hardware.launch.py use_fake_hardware:=false sim_mode:=false use_sim_time:=false use_rviz:=true servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml db:=true`
- Robot controllers: `joint_trajectory_controller` (ros2_control)
- Middleware: CycloneDDS with custom `cyclonedds.xml` (participant limit adjustments)

## Current State
- Script now computes and time-parameterises the MTC solution.
- Default behaviour: publish solution, keep the node alive, and wait for RViz **Exec** (manual execution).
- Optional `--auto-execute` flag re-enables immediate execution via `ExecuteTaskSolution` action.
- Controller still rejects trajectories if timestamps are missing or stage start-state diverges.
- Capturing controller goals requires recording hidden action topics (`--include-hidden-topics`).
- Conservatively parameterised motion (0.5 s between waypoints) executes successfully without drive faults.

## Attempts & Findings
### 1. Time Parameterisation in Script
- `_parameterize_solution()` sets waypoint durations via MTC’s C++ API; `_parameterize_solution_msg()` adds explicit `time_from_start` to each `JointTrajectoryPoint` in the message.
- Without time stamps, controller logs: `Time between points 0 and 1 is not strictly increasing`.
- Outcome: works when the action receives the patched message; fails otherwise.
- Increasing the waypoint spacing constant (`TIME_STEP = 0.5`) slows execution enough to avoid HAL drive faults.

### 2. Publishing to `/solution` for RViz
- Task solution published with QoS `{depth=1, RELIABLE, TRANSIENT_LOCAL}`.
- RViz sometimes shows solution entry in red or absent if message lacks stage metadata or stage IDs do not match.
- Removing/adding task from topic `/solution` refreshes display.

### 3. Controller Selection
- MTC warns: `trajectory of stage ... does not have any controllers`.
- Set `properties["controller"] = "joint_trajectory_controller"` on both `MoveTo` stages. Warning persists because Stage 2 (CurrentState) has no trajectory and defaults to empty controller list; acceptable but noise remains.

### 4. Execution Methods
- `task.execute(solution)` forwards solution to ExecuteTaskSolution capability but still used stale (zero-timestamp) data when executed before message patching.
- Switching to explicit `ExecuteTaskSolution` action call with the parameterised message ensures controller receives corrected trajectory.
- Script now exposes `--auto-execute` flag; default (without flag) publishes to `/solution` and leaves execution to RViz **Exec**.
- Example auto mode:
  ```bash
  python3 src/tormach_za_ros2_drivers/za6_moveit_config/scripts/mtc/za6_stored_state_sequence.py \
    --auto-execute \
    --ros-args --params-file \
    /home/pathpilot/Projects/za6_workspace/src/tormach_za_ros2_drivers/za6_moveit_config/config/mtc/za6_stored_state_sequence.params.yaml
  ```
- Example manual (default) mode—omit `--auto-execute`; press **Exec** in RViz after the script reports “Solution published…”.

### 5. Start State Alignment
- Execution aborts if robot state differs from solution start more than `allowed_start_tolerance` (0.01 rad). Example: joint_1 expected `0.515` but actual `0.360`.
- Fix: manually move to `WALL_NEUTRAL` or use RViz Stored States panel (`Set as Start`) before planning.

### 6. DDS Participant Exhaustion
- Repeated runs trigger `Failed to find a free participant index for domain 0` when residual processes are present.
- Recovery: `realtime stop`, kill `rtapi_*`, `hal_*`, `ros2 daemon` processes, ensure `CYCLONEDDS_URI` exported before CLI commands.

### 7. Recording Controller Input
- `ros2 bag record /joint_trajectory_controller/joint_trajectory` captured nothing (controller uses action interface).
- Correct topic: `/joint_trajectory_controller/follow_joint_trajectory/_action/send_goal` (requires `--include-hidden-topics`).
- Bag playback + `ros2 topic echo` confirms timestamps.

### 8. RViz Crashes
- Occur when pressing **Exec** after script already executed via action or when task entry references obsolete stage IDs.
- RViz MTC plugin expects solution metadata to match introspection data; removing/re-adding task helps, but once script executes automatically users should *not* press Exec.

### 9. Successful Slow Execution (Nov 9)
- Updated `stored_state_sequence.py` to introduce a shared `TIME_STEP = 0.5` (sec) applied to `_parameterize_solution()` and `_parameterize_solution_msg()`.
- Launched full stack with real hardware, positioned robot at `WALL_NEUTRAL`, and ran the script; no HAL faults (`0x0B000B00`) occurred.
- Robot completed both `MoveTo` stages and Drive State remained in `OPERATION ENABLED` throughout; RViz MTC pane showed one solution per stage.
- Confirms that the drive fault was caused by overly aggressive timing; further tuning can gradually reduce `TIME_STEP` if higher speed is required.
- Representative launch trace shows both trajectories accepted and completed (`joint_trajectory_controller` goal success at 1762735769–1762735779; see ROS log excerpt captured on Nov 9).

### 10. Remaining RViz Exec Issue — Mitigation Paths
- **Patch moveit2 core (preferred long-term)**
  - *Approach*: add time-parameterisation inside MTC’s C++ pipeline so each `robot_trajectory::RobotTrajectory` carries real timestamps before the introspection cache stores it.
  - *Pros*: fixes the root cause; RViz, scripts, and any other client see consistent timed trajectories without extra work; aligns with upstream expectations.
  - *Cons*: requires modifying / rebuilding moveit2 (potentially invasive); must upstream or maintain a patch set; needs C++ expertise and regression testing across other MTC demos.
- **Patch the MTC RViz plugin (workaround)**
  - *Approach*: detect zero timestamps when the user presses **Exec** and locally re-time the `RobotTrajectory` (e.g. run TOTG or apply a constant spacing) before handing it to `move_group`.
  - *Pros*: isolates change to visualization stack; easier to iterate on; no need to touch core planners.
  - *Cons*: duplicates time-parameterisation logic in RViz (risk of divergence); still leaves untimed data in other consumers (e.g. external tools using introspection); execution behaviour depends on which frontend launches the solution.

### 11. Relocating Customized Assets (Nov 9)
- Any tweaks to `moveit_task_constructor` demo scripts/configs (e.g. the modified `stored_state_sequence.py` and params) are being moved into our `tormach_za_ros2_drivers` repo under `za6_moveit_config/scripts/mtc` and `config/mtc`.
- Markdown write-ups produced during this effort (e.g. troubleshooting notes) should also live in the tormach repo so docs, scripts, and configs ship together.
- Rationale:
  - Keeps upstream dependency clean—no local patches that might be overwritten during updates.
  - Places ZA‑6 specific tooling alongside the rest of our robot config, which we control and can version upstream.
  - Simplifies deployment: launch files in the tormach repo can reference the local copies without depending on modified upstream packages.
- TODO: once the files are staged in `tormach_za_ros2_drivers`, remove any lingering changes in `src/moveit_task_constructor` (or plan to upstream a proper patch if the changes should live there long term).

## Next Steps
1. Investigate Stage 2 controller warning—may need to mark it as non-executing or ensure `sub_trajectory` retains controller metadata even when empty.
2. Capture controller goal after manual RViz execution (post-fix) to confirm timestamps.
3. Document reliable procedure to reset HAL/CycloneDDS states to avoid participant exhaustion.
4. Consider updating stored states if hardware deviates from `WALL_NEUTRAL`.

## Launch Troubleshooting (CycloneDDS participants)
When `hw_device_mgr` crashes with `Failed to find a free participant index for domain 0`, clean up and relaunch:

```bash
ros2 daemon stop || true
realtime stop || true
sudo pkill -f rtapi_msgd || true
sudo pkill -f rtapi_app || true
sudo pkill -f hal_mgr || true
pkill -f hw_device_mgr || true
pkill -f hal_io || true
pkill -f drive_state || true
pkill -f "ros2 launch" || true

ps aux | grep -E "rtapi|hal_|drive_state|ros2" | grep -v grep

export CYCLONEDDS_URI=/home/pathpilot/Projects/za6_workspace/install/za6_moveit_config/share/za6_moveit_config/config/cyclonedds.xml
ros2 daemon start
ros2 launch za6_moveit_config teleop_hardware.launch.py use_fake_hardware:=false sim_mode:=false use_use_time:=false use_rviz:=true servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml db:=true
```
If the CLI needs to run after launch, ensure the same `CYCLONEDDS_URI` is exported in that shell.

## Quick Procedure Recap
1. Launch stack; ensure custom CycloneDDS config exported.
2. Start script (`za6_stored_state_sequence.py` from `src/tormach_za_ros2_drivers/za6_moveit_config/scripts/mtc`), wait for `Solution published...`.
3. Robot currently moves automatically via action—do not press Exec.
4. After motion, press Enter to exit script.
5. To test manual Exec: modify script to skip action call and rely solely on RViz (future work).
