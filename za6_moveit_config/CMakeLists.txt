cmake_minimum_required(VERSION 3.22)
project(za6_moveit_config)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_ros REQUIRED)
find_package(moveit_servo REQUIRED)
find_package(moveit_core REQUIRED)
find_package(moveit_ros_planning REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_srvs REQUIRED)
find_package(xacro REQUIRED)

# Build static SRDF
xacro_add_xacro_file(config/za6.srdf.xacro config/za6.srdf)
# - add an abstract target to actually trigger the builds
add_custom_target(srdf_files ALL DEPENDS ${XACRO_OUTPUT_FILE})

# Build custom servo node executable
add_executable(za6_servo_node src/za6_servo_node.cpp)

target_include_directories(
  za6_servo_node
  PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${moveit_core_INCLUDE_DIRS}
  ${moveit_ros_planning_INCLUDE_DIRS}
  ${moveit_servo_INCLUDE_DIRS}
)

ament_target_dependencies(
  za6_servo_node
  moveit_servo
  moveit_core
  moveit_ros_planning
  rclcpp
  std_srvs
)

# Install custom servo node
install(
  TARGETS
    za6_servo_node
  RUNTIME DESTINATION
    lib/${PROJECT_NAME}
)

# Install Python helper scripts (preserve directory structure)
install(
  DIRECTORY
    scripts/
  DESTINATION
    lib/${PROJECT_NAME}
  FILES_MATCHING
    PATTERN "*.py"
    PATTERN "__pycache__" EXCLUDE
)

install(
  PROGRAMS
    scripts/gamepad_to_servo.py
    scripts/publish_frame_markers.py
    scripts/store_frames_to_warehouse.py
    scripts/load_frames_from_warehouse.py
    scripts/get_current_pose.py
    scripts/run_servo_with_manipulator.sh
  DESTINATION
    lib/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/mtc/za6_stored_state_sequence.py
  DESTINATION
    lib/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/mtc/mtc_pipeline_experiment.py
    scripts/diagnose_trajectory.py
  DESTINATION
    lib/${PROJECT_NAME}
  RENAME
    mtc_pipeline_experiment.py
)

install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME})
install(FILES .setup_assistant DESTINATION share/${PROJECT_NAME})
install(FILES ${XACRO_OUTPUT_FILE} DESTINATION share/${PROJECT_NAME}/config)

if(BUILD_TESTING)

  find_package(ament_cmake_copyright REQUIRED)
  ament_copyright()

  find_package(ament_cmake_xmllint REQUIRED)
  ament_xmllint()

  find_package(ament_cmake_pep257 REQUIRED)
  ament_pep257()
endif()

ament_package(CONFIG_EXTRAS "za6_moveit_config-extras.cmake")
