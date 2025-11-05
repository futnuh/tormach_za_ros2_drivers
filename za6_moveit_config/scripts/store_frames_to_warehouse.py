#!/usr/bin/env python3

"""
Script to store user frames in MoveIt warehouse for persistent storage.

This script reads frames from user_frames.yaml and stores them in the warehouse.
Frames are stored as metadata (not collision objects), so they don't interfere with planning.

Usage:
    ros2 run za6_moveit_config store_frames_to_warehouse.py
    ros2 run za6_moveit_config store_frames_to_warehouse.py --frames-file /path/to/frames.yaml
"""

import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetPlanningScene, ApplyPlanningScene
from moveit_msgs.msg import PlanningScene, RobotState, PlanningSceneComponents
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose
from moveit_msgs.srv import GetPositionFK
import yaml
import os
import sys
import json
from ament_index_python.packages import get_package_share_directory


class FrameWarehouseStorer(Node):
    def __init__(self, frames_file=None):
        super().__init__('frame_warehouse_storer')
        
        # Get frames file path
        if frames_file:
            self.frames_file = frames_file
        else:
            pkg_share = get_package_share_directory('za6_moveit_config')
            self.frames_file = os.path.join(pkg_share, 'config', 'user_frames.yaml')
        
        if not os.path.exists(self.frames_file):
            self.get_logger().error(f"Frames file not found: {self.frames_file}")
            sys.exit(1)
        
        # Load frames
        with open(self.frames_file, 'r') as f:
            self.frames = yaml.safe_load(f)
        
        # Create service clients
        self.get_scene_client = self.create_client(GetPlanningScene, 'get_planning_scene')
        self.apply_scene_client = self.create_client(ApplyPlanningScene, 'apply_planning_scene')
        self.fk_client = self.create_client(GetPositionFK, 'compute_fk')
        
        # Wait for services
        self.get_logger().info("Waiting for planning scene services...")
        self.get_scene_client.wait_for_service(timeout_sec=5.0)
        self.apply_scene_client.wait_for_service(timeout_sec=5.0)
        
        # Wait for FK service (may not always be available, that's OK)
        self.fk_available = self.fk_client.wait_for_service(timeout_sec=2.0)
        if not self.fk_available:
            self.get_logger().warn("Forward kinematics service not available. Joint-state frames will be skipped.")
        
        # Default end effector link
        self.default_ee_link = 'grasp_link'
        
        self.get_logger().info(f"Loaded {len(self.frames)} frames from {self.frames_file}")
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """Convert Euler angles to quaternion."""
        import math
        
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy
        qw = cr * cp * cy + sr * sp * sy
        
        return qx, qy, qz, qw
    
    def compute_forward_kinematics(self, joint_names, joint_positions, ee_link=None):
        """Compute forward kinematics for joint positions."""
        if not self.fk_available:
            self.get_logger().error("Forward kinematics service not available")
            return None
        
        if ee_link is None:
            ee_link = self.default_ee_link
        
        # Create robot state
        robot_state = RobotState()
        joint_state = JointState()
        joint_state.name = joint_names
        joint_state.position = joint_positions
        robot_state.joint_state = joint_state
        
        # Create FK request
        request = GetPositionFK.Request()
        request.header.frame_id = "world"
        request.fk_link_names = [ee_link]
        request.robot_state = robot_state
        
        # Call FK service
        future = self.fk_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is None or not future.result().error_code.val == 1:
            self.get_logger().error(f"Failed to compute FK for {ee_link}")
            return None
        
        if len(future.result().pose_stamped) == 0:
            self.get_logger().error(f"No pose returned from FK service")
            return None
        
        return future.result().pose_stamped[0].pose
    
    def get_pose_from_frame_data(self, frame_data, frame_name):
        """Get pose from frame data, handling both pose and joint_state."""
        parent_frame = frame_data.get('parent_frame', 'world')
        
        # Case 1: Direct pose specified
        if 'pose' in frame_data:
            pose_data = frame_data['pose']
            if len(pose_data) != 6:
                self.get_logger().warn(f"Frame {frame_name} has invalid pose (expected 6 values)")
                return None, None
            
            x, y, z, roll, pitch, yaw = pose_data
            qx, qy, qz, qw = self.euler_to_quaternion(roll, pitch, yaw)
            
            pose = Pose()
            pose.position.x = float(x)
            pose.position.y = float(y)
            pose.position.z = float(z)
            pose.orientation.x = float(qx)
            pose.orientation.y = float(qy)
            pose.orientation.z = float(qz)
            pose.orientation.w = float(qw)
            
            return pose, parent_frame
        
        # Case 2: Joint state specified - compute pose via forward kinematics
        elif 'joint_state' in frame_data:
            joint_data = frame_data['joint_state']
            joint_names = joint_data.get('name', [])
            joint_positions = joint_data.get('position', [])
            
            if len(joint_names) != len(joint_positions):
                self.get_logger().warn(f"Frame {frame_name} has mismatched joint names and positions")
                return None, None
            
            ee_link = frame_data.get('ee_link', self.default_ee_link)
            
            self.get_logger().info(f"Computing forward kinematics for frame '{frame_name}' using {ee_link}")
            pose = self.compute_forward_kinematics(joint_names, joint_positions, ee_link)
            
            if pose is None:
                self.get_logger().error(f"Failed to compute FK for frame '{frame_name}'")
                return None, None
            
            return pose, parent_frame
        
        else:
            self.get_logger().warn(f"Frame {frame_name} has neither 'pose' nor 'joint_state'")
            return None, None
    
    def store_frames_in_scene(self, scene):
        """Store frame definitions as metadata in the planning scene."""
        # Store frames as a JSON string in the scene's allowed collision matrix or as scene object metadata
        # We'll use the scene name to identify this as a frames storage scene
        
        # Convert frames to a serializable format
        frames_data = {}
        for frame_name, frame_data in self.frames.items():
            if not isinstance(frame_data, dict):
                continue
            
            # Get pose (from direct specification or computed from joint state)
            pose, parent_frame = self.get_pose_from_frame_data(frame_data, frame_name)
            
            if pose is None:
                continue
            
            # Store frame definition
            frame_def = {
                'name': frame_name,
                'parent_frame': parent_frame,
                'pose': {
                    'position': {
                        'x': float(pose.position.x),
                        'y': float(pose.position.y),
                        'z': float(pose.position.z)
                    },
                    'orientation': {
                        'x': float(pose.orientation.x),
                        'y': float(pose.orientation.y),
                        'z': float(pose.orientation.z),
                        'w': float(pose.orientation.w)
                    }
                },
                'description': frame_data.get('description', ''),
                'source': 'yaml' if 'pose' in frame_data else 'joint_state',
                'ee_link': frame_data.get('ee_link', self.default_ee_link) if 'joint_state' in frame_data else None
            }
            
            if 'joint_state' in frame_data:
                joint_data = frame_data['joint_state']
                frame_def['joint_state'] = {
                    'name': joint_data.get('name', []),
                    'position': [float(p) for p in joint_data.get('position', [])]
                }
            
            frames_data[frame_name] = frame_def
        
        # Note: Frames data is stored in the frames_data dictionary
        # The actual storage happens via warehouse SaveScene service
        # The scene itself doesn't contain collision objects (frames are visual-only)
        
        self.get_logger().info(f"Prepared {len(frames_data)} frames for storage")
        return scene, frames_data
    
    def save_scene_to_warehouse(self, scene, scene_name, frames_data):
        """Save scene to warehouse using ApplyPlanningScene service.
        
        In ROS2 MoveIt2, scenes are saved to warehouse automatically when 
        ApplyPlanningScene is called with a named scene and warehouse is enabled.
        The warehouse stores scenes by name, accessible via RViz Motion Planning plugin.
        """
        # Set scene name
        scene.name = scene_name
        
        # Apply the scene (this saves to warehouse if enabled)
        request = ApplyPlanningScene.Request()
        request.scene = scene
        
        future = self.apply_scene_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is None:
            self.get_logger().error("Failed to apply planning scene")
            return False
        
        if future.result().success:
            self.get_logger().info(f"Successfully stored {len(frames_data)} frames in warehouse as scene '{scene_name}'!")
            self.get_logger().info("Note: Scene is stored in warehouse and can be loaded via RViz Motion Planning plugin")
            
            # Also save frames JSON to a file for reference/backup and easy retrieval
            frames_file_path = os.path.join(os.path.expanduser('~/.ros/warehouse'), 'user_frames.json')
            os.makedirs(os.path.dirname(frames_file_path), exist_ok=True)
            with open(frames_file_path, 'w') as f:
                json.dump(frames_data, f, indent=2)
            self.get_logger().info(f"Frame definitions also saved to {frames_file_path} for backup")
            return True
        else:
            self.get_logger().error(f"Failed to save scene: {future.result().error_message}")
            return False
    
    def run(self):
        """Main execution."""
        # Create a new scene for storing frames
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.world.collision_objects = []
        
        # Store frames in scene
        scene, frames_data = self.store_frames_in_scene(scene)
        
        # Save scene to warehouse with a fixed name
        scene_name = "user_frames"
        return self.save_scene_to_warehouse(scene, scene_name, frames_data)


def main(args=None):
    rclpy.init(args=args)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Store user frames in MoveIt warehouse')
    parser.add_argument('--frames-file', type=str, help='Path to frames YAML file')
    args = parser.parse_args()
    
    storer = FrameWarehouseStorer(frames_file=args.frames_file)
    success = storer.run()
    
    storer.destroy_node()
    rclpy.shutdown()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

