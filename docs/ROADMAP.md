# ZA6 Roadmap

## A. Restore RViz Exec for MTC Tasks
- **Objective**: Enable the RViz Task Constructor panel to execute programmatically generated solutions via the **Exec** button.
- **Context**: RViz reads untimed `robot_trajectory::RobotTrajectory` data from the MTC introspection cache, so the controller rejects Exec requests.
- **Plan**:
  - Patch MoveIt core (or RViz plugin) so cached trajectories are time-parameterized before RViz consumes them.
  - Rebuild the MoveIt stack in the workspace and verify the fix by planning and executing via RViz.

## B. Evaluate MTC for Complex Task Orchestration
- **Objective**: Determine whether MTC can coordinate mixed motion and non-motion subtasks (digital I/O, external services, vision feedback, etc.).
- **Plan**:
  - Prototype a task tree that includes both motion stages and stages that toggle I/O or call ROS 2 services.
  - Run the prototype on real hardware (or high-fidelity simulation) to validate timing, error handling, and viability.
  - Decide if MTC remains the orchestration backbone or if we need complementary tooling.

## C. Harden Docker Image Dependencies ✅
- **Objective**: Bake all runtime dependencies (see `docs/DOCKER_IMAGE_DEPENDENCIES.md`) into the Docker image so fresh containers are ready to build and launch.
- **Status**: Completed — `ros_custom/install_moveit2_deps.sh` now installs the full dependency set (including `ros-humble-py-binding-tools`), the hardened image rebuilts cleanly, and a fresh container passed the throttled `colcon build` plus `teleop_hardware.launch.py` smoke test in fake hardware mode.
- **Future upkeep**:
  - Keep `docs/DOCKER_IMAGE_DEPENDENCIES.md` and the install script synchronized when adding new runtime requirements.
  - Record image tags after each verification run so CI and operators can pull a known-good baseline.

## D. Automate RViz Layout & Warehouse Setup
- **Objective**: Remove the manual RViz setup steps performed after each launch.
- **Plan**:
  - Capture the desired RViz configuration (panels, docking, displays, alpha settings) into a dedicated `.rviz` file and use it by default.
  - Add launch-time helpers to auto-connect to the Motion Planning Warehouse and manage stored states.
  - Test so RViz opens ready-to-plan with zero manual adjustments.

## E. Surface Drive & Teleop State in RViz
- **Objective**: Provide live drive status, enable/disable controls, and teleoperation mode indicators directly in RViz.
- **Plan**:
  - Design a custom RViz panel (or companion UI) with buttons tied to the `enable_drives`/`disable_drives` services.
  - Display teleop/interactive mode and joint vs. Cartesian mode by subscribing to relevant status topics.
  - Iterate on UI layout with stakeholders and integrate the panel via launch or plugin configuration.

