# MTC Pipeline Experiment Plan

## Goal
- Validate whether MoveIt Task Constructor (MTC) can orchestrate a mixed workflow that interleaves motion planning, discrete I/O, service calls, and vision feedback without additional orchestration tooling.
- Capture gaps that would require upstream patches or companion services so we can decide if MTC remains the primary task engine for the ZA6.

## Current Implementation Status (2025-11-11)
- `mtc_pipeline_experiment.py` now runs end-to-end on hardware with synchronized gripper toggles and motion execution when invoked via `--auto-execute --wait-for-feedback`.
- Added a temporary patch to the cloned `moveit_task_constructor` sources exposing `Stage::setExecuteCallback()` and `ModifyPlanningScene::setCallback()` to Python. The binding lives in `core/python/bindings/src/core.cpp`, with supporting C++ changes in `core/include/moveit/task_constructor/stage.{h,p.h}` and `core/src/stage.cpp`. **These edits must be rebuilt (`colcon build --packages-select moveit_task_constructor_core ...`) and will need to be carried forward as a patch or fork.**
- `create_toggle_stage()` now instantiates a `ModifyPlanningScene` stage and registers a Python execute callback, so the digital output fires only during execution. The helper returns a boolean result to signal success/failure back into the pipeline.
- HAL helper `za6_moveit_config/scripts/io/gripper_io.py` publishes to `/hal_io/dout01` and mirrors state on `/hal_io/digital_out_1`, honoring BEST_EFFORT QoS; the same helper is reused by the execute callback.
- OMPL configuration parameters are declared on the MTC node via `configure_ompl_pipeline()` (which now flattens nested YAML into discrete ROS parameters), and `PipelinePlanner::create()` accepts a direct plugin override (`setPlanningPlugin()`), so the pipeline loads `ompl_interface/OMPLPlanner` without falling back to CHOMP. Planner warnings about missing configurations are gone; only the standard “planning volume not specified” notice remains. The move group logs confirm successful execution despite the `error_code: 1` print, which maps to `MoveItErrorCode::SUCCESS`.
- `ExecuteTaskSolutionCapability` applies `IterativeParabolicTimeParameterization` to each sub-trajectory with the same scaling RViz uses (velocity 0.05, acceleration 0.08), eliminating the stop/start behavior while staying within drive limits. We also add a 500 ms pre/post pause around the gripper toggle to give HAL time to react.
- `{`24:latest path? Need update. change to new logfile? Should we reference new run? maybe mention path with timestamp? Use new file? we can reference same path or new. maybe mention SUCCEEDED.}
- Latest debugging (2025-11-13) showed the Python `rclcpp.Node` shim behind MTC lacks `has_parameter()/get_parameter()/list_parameters`. The new override path sets `pipeline.planning_plugin = "ompl_interface/OMPLPlanner"` in the experiment script, eliminating the CHOMP warning.
- RViz “Exec” continues to replay untimed cached trajectories; auto-execute is the only safe execution path until an upstream fix is implemented.

## Representative Scenario
- **Task theme**: Machine tending part pickup with in-line inspection.
- **Stages**:
  - Retrieve robot from a stored start state (warehouse scene).
  - Toggle gripper I/O to open.
  - Move to a pre-grasp waypoint.
  - Call a vision service (`/vision/detect_part`) to confirm part presence.
  - Branch on service result:
    - **Success path**: move to grasp, close gripper, retreat, place part.
    - **Failure path**: signal an operator alert stage, park safely.
  - Publish execution summary (topic or log) to verify post-processing.

## Technical Checklist
- Leverage existing MTC stages:
  - Use Task Constructor `GeneratePose` / `CurrentState` for pose setup.
  - `ApplyPlanningScene` or custom Python stage for I/O toggles.
  - `ComputeIK` + `MoveTo` stages for motion segments.
  - Python `MonitoringGenerator` to call the vision service and branch.
- Confirm bindings support for above stages in Python; fall back to C++ stage wrappers if needed.
- Wire controller selection (`joint_trajectory_controller`) on motion stages.

## Evaluation Metrics
- **Scheduling**: ability to insert waits or rate limits between I/O and motion.
- **Error propagation**: meaningful exception context when a stage fails (service timeout, plan invalid, controller rejection).
- **Real-time coordination**: ensure motion stages respect teleop safety (start state alignment, brake releases).
- **Introspection**: RViz Task Constructor panel shows stage results and allows replay/debugging.
- **Recovery**: confirm that failing the vision branch returns the robot to a safe stop state without manual cleanup.

## Environment Setup
- Run in fake hardware first, then exercise on real hardware once stable.
- Ensure hardened Docker image is in use; source workspace inside container.
- Export CycloneDDS config so CLI tools reach all nodes:
  ```bash
  source install/setup.bash
  export CYCLONEDDS_URI=/home/pathpilot/Projects/za6_workspace/install/za6_moveit_config/share/za6_moveit_config/config/cyclonedds.xml
  ```
- Launch baseline stack with warehouse enabled:
  ```bash
  ros2 launch za6_moveit_config teleop_hardware.launch.py \
    use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
    use_rviz:=true \
    servo_config:=servo_config.yaml gamepad_config:=gamepad_config.yaml \
    db:=true
  ```
- Prepare mock services for dry-runs (e.g., Python node that mimics `detect_part` responses).

## Experiment Workflow
1. **Prototype pipeline** in Python (`mtc_pipeline_experiment.py`) within `za6_moveit_config/scripts/mtc`.
2. **Stage validation**:
   - Unit test non-motion stages standalone (service calls, I/O toggles) with `ros2 run`.
   - Verify store/load of start states via warehouse.
3. **Plan only**: `--auto-execute false` to review stage outputs in RViz.
4. **Timed execution**: reuse `_parameterize_solution` helpers to keep trajectories controller-safe.
5. **Failure injection**: force vision service timeout to observe branch and recovery.
6. **Real hardware check** (optional final step after fake-hardware success).

## Data Capture & Analysis
- Use `ros2 bag record --include-hidden-topics` for controller action feedback.
- Save Task Constructor logs and RViz introspection snapshots for documentation.
- Record timing of each stage (wall clock) and latencies of service calls.
- Document controller responses (`joint_trajectory_controller` logs) to confirm smooth execution.

## Risks & Open Questions
- Python bindings may not expose all desired stage APIs; might require temporary C++ helper.
- RViz Exec still uses untimed trajectories; rely on scripted auto-execute mode for now.
- Service call stages could block the pipeline; need timeout handling to avoid deadlocks.
- Branching complexity may impact debuggability—ensure logging and panel labels are clear.
- Tool frame definition is needed eventually for realistic grasp planning; see “Deferred Work” note below.

## Next Steps
- Implement the scripted pipeline following this plan.
- Update documentation (`MTC_EXPERIMENTS.md`, roadmap) with findings.
- Decide whether additional orchestration tooling (state machines, behavior trees) is necessary based on experiment outcomes.

## Upstream Follow-up (MoveIt 2 / MTC Core)
- Submit the local patch adding `PipelinePlanner::setPlanningPlugin()` and the Python binding exposure upstream.
- Optional future work: extend the Python `rclcpp::Node` binding to expose `has_parameter()` / `get_parameter()` / `list_parameters()` so the legacy lookup path can be restored without overrides.
- Consider upstreaming a quality-of-life fix so `TrajectoryExecutionInfo` coming from Python stages retains controller names, avoiding warnings like “stage N has no controllers.”

---

## Gripper Toggle Implementation Notes (Phase 1 Focus)

- **Scope decision**: first iteration will target roadmap items 2 & 3 (HAL I/O helper and MTC stage) and defer physical tool-frame modelling.

### 2. HAL Digital Output Helper (`DOUT01`)
- Wrap existing `/hal_io/dout01` interfaces in a dedicated helper module (e.g., `za6_moveit_config/scripts/io/gripper_io.py`).
- Provide high-level functions:
  - `set_gripper(open: bool)` → publish to `hal_io/dout01`.
  - Optional confirmation hook (`wait_for_feedback()`), reading `/hal_io/dout01` or a diagnostic topic for acknowledgement.
- Handle configuration (latched vs. momentary command, expected True/False semantics) and document default behavior in the helper.
- Keep module self-contained so non-MTC scripts can reuse it.

### 3. MTC Gripper Toggle Stage
- Implement a Python `PropagatingEitherWay` stage (or helper function) that:
  - Calls `gripper_io.set_gripper(True/False)` when executed.
  - Optionally inserts a short sleep or polls for confirmation before allowing the task to progress.
  - Emits meaningful debug messages for RViz introspection.
- Insert stage within the new `mtc_pipeline_experiment.py` task sequence between motion segments (open before approach, close after grasp).
- Maintain compatibility with `_parameterize_solution` to keep trajectory execution safe when `--auto-execute` is enabled.

### Deferred Work: Tool Frame Modelling
- Adding a physical gripper model and tool frame remains on the roadmap but is out of scope for this phase.
- Plan to revisit once I/O automation proves stable; updates would touch `za6_description` URDF, SRDF, and MoveIt configuration.

