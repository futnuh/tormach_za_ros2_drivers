/*********************************************************************
 * Software License Agreement (BSD License)
 *
 *  Copyright (c) 2025 Tormach, Inc.
 *********************************************************************/

/*      Title     : za6_servo_node.cpp
 *      Desc      : Custom servo node that properly initializes MoveIt Servo
 *                  with ZA6-specific move group name ('manipulator')
 */

#include <memory>
#include <moveit_servo/servo_node.h>
#include <rclcpp/rclcpp.hpp>
#include <signal.h>

using moveit_servo::ServoNode;

int main(int argc, char* argv[])
{
  rclcpp::init(argc, argv);
  
  // Create node options with ZA6-specific parameters
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args", "-p", "move_group_name:=manipulator"});

  // Create ServoNode with the options
  auto servo_node = std::make_shared<ServoNode>(options);

  RCLCPP_INFO(rclcpp::get_logger("za6_servo"), "ZA6 servo node initialized with move group: manipulator");

  // Spin until shutdown requested
  rclcpp::spin(servo_node->get_node_base_interface());
  rclcpp::shutdown();

  return 0;
}
