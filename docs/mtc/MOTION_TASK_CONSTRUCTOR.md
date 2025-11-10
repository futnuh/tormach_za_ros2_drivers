# Motion Task Constructor Integration

We want to add the MoveIt Task Constructor (MTC) packages to our fork so we can prototype task-based planning workflows (grasping, sequences, etc.) alongside our RViz enhancements. To keep the setup repeatable and minimize rebuild time, follow the steps below.

## Workflow

1. **Stay on the feature branch**
   - Branch off the current RViz feature work: `feature/add-task-constructor`.
   - All recent UI improvements carry forward while we experiment with MTC.

2. **Update the workspace manifest**
   - Append MTC to `moveit2.repos`:
     ```yaml
     moveit_task_constructor:
       type: git
       url: https://github.com/ros-planning/moveit_task_constructor.git
       version: humble
     ```
   - This keeps the repository list reproducible for future checkouts.

3. **Import sources**
   - From the workspace root (`/home/pathpilot/Projects/za6_workspace`):
     ```bash
     vcs import src < src/moveit2/moveit2.repos --skip-existing
     ```
   - Only the new task-constructor packages are cloned; everything else is left untouched.

4. **Install dependencies**
   - Ensure the container has all required packages:
     ```bash
     rosdep install --from-paths src --ignore-src -r -y
     ```
   - Run inside the `ros2-devel` container after sourcing the ROS setup.

5. **Build incrementally**
   - Limit the build to the new packages to avoid rebuilding all of MoveIt:
     ```bash
     MAKEFLAGS=-j1 colcon build \
       --packages-select moveit_task_constructor_msgs rviz_marker_tools \
                         moveit_task_constructor_core moveit_task_constructor_capabilities \
                         moveit_task_constructor_visualization moveit_task_constructor_demo \
       --executor sequential --parallel-workers 1 \
       --cmake-args -DCMAKE_BUILD_PARALLEL_LEVEL=1
     ```
   - Adjust the package list if more components are needed.

6. **Test and iterate**
   - Run the provided demos or load the plugins in RViz/MoveIt to verify integration.
   - To expose the RViz Task Constructor panel, build `moveit_task_constructor_visualization`, re-source the workspace, then in RViz select `Panels → Add New Panel… → Task Constructor`.
   - Capture any additional runtime dependencies and add them to the Docker build scripts (see `DOCKER_IMAGE_DEPENDENCIES.md`).
   - A helper script `stored_state_sequence.py` (installed with `moveit_task_constructor_demo`) builds a two-stage task that moves from `WALL_NEUTRAL` to `DOOR_FACING_NEUTRAL`. Launch the teleop stack, then in another shell run:
     ```bash
     ros2 run moveit_task_constructor_demo stored_state_sequence.py
     ```
     The RViz Task Constructor panel will display the generated task and its solution.

7. **Commit and push**
   - Commit the `moveit2.repos` change and any new scripts/configuration.
   - Push the branch: `git push origin feature/add-task-constructor`.

Following this process keeps the rebuild time minimal (only the new packages compile) and makes the workspace reproducible for teammates or CI pipelines.

## Ownership & Relocation (Nov 9)
- Any derivative documentation (including this file) and custom scripts/configuration now belong in the `tormach_za_ros2_drivers` repository so ZA-6 specific workships with our maintained packages.
- Action items:
  - Copy this guide and the accompanying troubleshooting notes into the tormach repo under `docs/` (or similar).
  - Update references so launch instructions and helpers point to the relocated assets.
  - Remove lingering Markdown copies from `src/moveit2` once the migration is complete to avoid divergence.


