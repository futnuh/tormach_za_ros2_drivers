#!/usr/bin/env python3

"""
Script to get the current end-effector pose and output in user_frames.yaml format.

This script:
1. Gets the current end-effector pose from TF or MoveIt
2. Converts it to [x, y, z, roll, pitch, yaw] format
3. Outputs in the format needed for user_frames.yaml

Usage:
    ros2 run za6_moveit_config get_current_pose.py
    ros2 run za6_moveit_config get_current_pose.py --ee-link grasp_link --parent-frame world
"""

import rclpy
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer
from geometry_msgs.msg import TransformStamped
import math
import sys


class PoseGetter(Node):
    def __init__(self, ee_link='grasp_link', parent_frame='world'):
        super().__init__('pose_getter')
        
        self.ee_link = ee_link
        self.parent_frame = parent_frame
        
        # Create TF buffer and listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        self.get_logger().info(f"Waiting for transform from {parent_frame} to {ee_link}...")
    
    def quaternion_to_euler(self, qx, qy, qz, qw):
        """Convert quaternion to Euler angles (roll, pitch, yaw)."""
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (qw * qx + qy * qz)
        cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (qw * qy - qz * qx)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (qw * qz + qx * qy)
        cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return roll, pitch, yaw
    
    def get_current_pose(self, timeout_sec=5.0):
        """Get current pose from TF."""
        try:
            # Wait for transform (use latest available time)
            transform = self.tf_buffer.lookup_transform(
                self.parent_frame,
                self.ee_link,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=timeout_sec)
            )
            
            # Extract position
            x = transform.transform.translation.x
            y = transform.transform.translation.y
            z = transform.transform.translation.z
            
            # Extract orientation and convert to Euler
            qx = transform.transform.rotation.x
            qy = transform.transform.rotation.y
            qz = transform.transform.rotation.z
            qw = transform.transform.rotation.w
            
            roll, pitch, yaw = self.quaternion_to_euler(qx, qy, qz, qw)
            
            return [x, y, z, roll, pitch, yaw]
            
        except Exception as e:
            self.get_logger().error(f"Failed to get transform: {e}")
            return None
    
    def format_for_yaml(self, pose, frame_name="my_frame"):
        """Format pose as YAML entry for user_frames.yaml."""
        x, y, z, roll, pitch, yaw = pose
        
        # Format with reasonable precision
        x_str = f"{x:.6f}".rstrip('0').rstrip('.')
        y_str = f"{y:.6f}".rstrip('0').rstrip('.')
        z_str = f"{z:.6f}".rstrip('0').rstrip('.')
        roll_str = f"{roll:.6f}".rstrip('0').rstrip('.')
        pitch_str = f"{pitch:.6f}".rstrip('0').rstrip('.')
        yaw_str = f"{yaw:.6f}".rstrip('0').rstrip('.')
        
        yaml_entry = f"""# Frame: {frame_name}
{frame_name}:
  parent_frame: {self.parent_frame}
  pose: [{x_str}, {y_str}, {z_str}, {roll_str}, {pitch_str}, {yaw_str}]
  description: "Frame captured via teleoperation"
"""
        
        return yaml_entry
    
    def run(self):
        """Main execution."""
        # Wait for TF buffer to populate
        import time
        time.sleep(1.0)  # Give TF time to populate
        
        # Try to get current pose (with retries)
        pose = None
        for attempt in range(5):
            pose = self.get_current_pose(timeout_sec=2.0)
            if pose is not None:
                break
            self.get_logger().warn(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(0.5)
        
        if pose is None:
            self.get_logger().error("Could not get current pose after multiple attempts")
            self.get_logger().error(f"Make sure robot is running and TF is publishing from {self.parent_frame} to {self.ee_link}")
            return False
        
        x, y, z, roll, pitch, yaw = pose
        
        # Print pose in different formats
        print("\n" + "="*60)
        print("Current End-Effector Pose")
        print("="*60)
        print(f"End-Effector Link: {self.ee_link}")
        print(f"Parent Frame: {self.parent_frame}")
        print(f"\nPosition (meters):")
        print(f"  X: {x:.6f}")
        print(f"  Y: {y:.6f}")
        print(f"  Z: {z:.6f}")
        print(f"\nOrientation (radians):")
        print(f"  Roll:  {roll:.6f}")
        print(f"  Pitch: {pitch:.6f}")
        print(f"  Yaw:   {yaw:.6f}")
        print(f"\nOrientation (degrees):")
        print(f"  Roll:  {math.degrees(roll):.2f}°")
        print(f"  Pitch: {math.degrees(pitch):.2f}°")
        print(f"  Yaw:   {math.degrees(yaw):.2f}°")
        print("\n" + "="*60)
        print("YAML Format (copy this to user_frames.yaml):")
        print("="*60)
        
        # Format as array
        print(f"\npose: [{x:.6f}, {y:.6f}, {z:.6f}, {roll:.6f}, {pitch:.6f}, {yaw:.6f}]")
        
        # Full YAML entry
        print("\nFull YAML entry:")
        print(self.format_for_yaml(pose, "my_frame"))
        
        print("="*60 + "\n")
        
        return True


def main(args=None):
    rclpy.init(args=args)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Get current end-effector pose')
    parser.add_argument('--ee-link', type=str, default='grasp_link',
                       help='End-effector link name (default: grasp_link)')
    parser.add_argument('--parent-frame', type=str, default='world',
                       help='Parent frame name (default: world)')
    args = parser.parse_args()
    
    getter = PoseGetter(ee_link=args.ee_link, parent_frame=args.parent_frame)
    success = getter.run()
    
    getter.destroy_node()
    rclpy.shutdown()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

