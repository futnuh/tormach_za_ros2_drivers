#!/usr/bin/env python3

"""
Script to load user frames from MoveIt warehouse.

This script loads frames that were previously stored in the warehouse
and can export them to YAML or use them directly.

Usage:
    ros2 run za6_moveit_config load_frames_from_warehouse.py
    ros2 run za6_moveit_config load_frames_from_warehouse.py --export-yaml /path/to/output.yaml
"""

import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetPlanningScene
from moveit_msgs.msg import PlanningSceneComponents
import yaml
import os
import sys
import json
import math


class FrameWarehouseLoader(Node):
    def __init__(self):
        super().__init__('frame_warehouse_loader')
        
        # Note: In ROS2 MoveIt2, warehouse scenes are managed by the warehouse service
        # and accessed via RViz Motion Planning plugin. The actual service interfaces
        # for listing/getting scenes don't exist as separate ROS2 services.
        # We load frames from the backup JSON file that was created during storage.
        
        self.get_logger().info("Loading frames from warehouse backup file...")
    
    def load_frames_from_warehouse(self):
        """Load frames from warehouse backup JSON file.
        
        In ROS2 MoveIt2, warehouse scenes are stored automatically when ApplyPlanningScene
        is called. However, the service interfaces to list/get scenes programmatically
        are not exposed as separate ROS2 services. The frames data is stored as a 
        backup JSON file for easy retrieval.
        """
        # Load frames JSON from backup file
        frames_file_path = os.path.join(os.path.expanduser('~/.ros/warehouse'), 'user_frames.json')
        
        if not os.path.exists(frames_file_path):
            self.get_logger().warn(f"Warehouse frames file not found: {frames_file_path}")
            self.get_logger().info("Try running 'ros2 run za6_moveit_config store_frames_to_warehouse.py' first")
            return None
        
        try:
            with open(frames_file_path, 'r') as f:
                frames_data = json.load(f)
            self.get_logger().info(f"Loaded {len(frames_data)} frames from warehouse backup file")
            self.get_logger().info(f"Note: Scene 'user_frames' is also stored in warehouse database")
            self.get_logger().info(f"      Load it via RViz Motion Planning plugin → Planning → Load Scene")
            return frames_data
        except Exception as e:
            self.get_logger().error(f"Failed to load frames from backup file: {e}")
            return None
    
    def frames_to_yaml(self, frames_data, output_file):
        """Convert frames data to YAML format."""
        yaml_frames = {}
        
        for frame_name, frame_def in frames_data.items():
            yaml_frame = {}
            
            # Set parent frame
            yaml_frame['parent_frame'] = frame_def.get('parent_frame', 'world')
            
            # Convert pose back to [x, y, z, roll, pitch, yaw] format
            if 'pose' in frame_def:
                pose = frame_def['pose']
                pos = pose['position']
                orient = pose['orientation']
                
                # Convert quaternion to Euler (approximate - full conversion would be better)
                # For now, if we have joint_state source, use that instead
                if frame_def.get('source') == 'joint_state' and 'joint_state' in frame_def:
                    yaml_frame['joint_state'] = frame_def['joint_state']
                    if 'ee_link' in frame_def:
                        yaml_frame['ee_link'] = frame_def['ee_link']
                else:
                    # For pose-based frames, we need to convert quaternion to Euler
                    # This is a simplified conversion
                    import math
                    qx, qy, qz, qw = orient['x'], orient['y'], orient['z'], orient['w']
                    
                    # Roll (x-axis rotation)
                    sinr_cosp = 2 * (qw * qx + qy * qz)
                    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
                    roll = math.atan2(sinr_cosp, cosr_cosp)
                    
                    # Pitch (y-axis rotation)
                    sinp = 2 * (qw * qy - qz * qx)
                    if abs(sinp) >= 1:
                        pitch = math.copysign(math.pi / 2, sinp)
                    else:
                        pitch = math.asin(sinp)
                    
                    # Yaw (z-axis rotation)
                    siny_cosp = 2 * (qw * qz + qx * qy)
                    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
                    yaw = math.atan2(siny_cosp, cosy_cosp)
                    
                    yaml_frame['pose'] = [
                        float(pos['x']),
                        float(pos['y']),
                        float(pos['z']),
                        float(roll),
                        float(pitch),
                        float(yaw)
                    ]
            
            # Add description if available
            if 'description' in frame_def:
                yaml_frame['description'] = frame_def['description']
            
            yaml_frames[frame_name] = yaml_frame
        
        # Write YAML file
        with open(output_file, 'w') as f:
            yaml.dump(yaml_frames, f, default_flow_style=False, sort_keys=False)
        
        self.get_logger().info(f"Exported {len(yaml_frames)} frames to {output_file}")
        return True
    
    def run(self, export_yaml=None):
        """Main execution."""
        # Load frames from warehouse
        frames_data = self.load_frames_from_warehouse()
        
        if frames_data is None:
            self.get_logger().error("No frames found in warehouse")
            return False
        
        # Export to YAML if requested
        if export_yaml:
            return self.frames_to_yaml(frames_data, export_yaml)
        
        # Otherwise just print info
        self.get_logger().info(f"Loaded {len(frames_data)} frames from warehouse:")
        for frame_name, frame_def in frames_data.items():
            pos = frame_def['pose']['position']
            self.get_logger().info(f"  - {frame_name}: [{pos['x']:.3f}, {pos['y']:.3f}, {pos['z']:.3f}]")
        
        return True


def main(args=None):
    rclpy.init(args=args)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Load user frames from MoveIt warehouse')
    parser.add_argument('--export-yaml', type=str, help='Export frames to YAML file')
    args = parser.parse_args()
    
    loader = FrameWarehouseLoader()
    success = loader.run(export_yaml=args.export_yaml)
    
    loader.destroy_node()
    rclpy.shutdown()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

