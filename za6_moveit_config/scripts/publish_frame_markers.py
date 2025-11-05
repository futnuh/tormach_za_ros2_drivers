#!/usr/bin/env python3

"""
Script to publish user frames as visualization markers with clear x, y, z axes.

This script reads frames from user_frames.yaml and publishes them as:
1. TF transforms (for reference frame)
2. RViz visualization markers (axes arrows) for visual identification
3. NOT as collision objects (planner ignores them)

Usage:
    ros2 run za6_moveit_config publish_frame_markers.py
    ros2 run za6_moveit_config publish_frame_markers.py --frames-file /path/to/frames.yaml
"""

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Pose, Point, Vector3
from std_msgs.msg import ColorRGBA, Header
from moveit_msgs.srv import GetPositionFK
from moveit_msgs.msg import RobotState
from sensor_msgs.msg import JointState
import yaml
import os
import sys
from ament_index_python.packages import get_package_share_directory


class FrameMarkerPublisher(Node):
    def __init__(self, frames_file=None, load_from_warehouse=False):
        super().__init__('frame_marker_publisher')
        
        self.load_from_warehouse = load_from_warehouse
        self.frames = {}
        
        if load_from_warehouse:
            # Load frames from warehouse
            self.load_frames_from_warehouse()
        else:
            # Get frames file path
            if frames_file:
                self.frames_file = frames_file
            else:
                pkg_share = get_package_share_directory('za6_moveit_config')
                self.frames_file = os.path.join(pkg_share, 'config', 'user_frames.yaml')
            
            if not os.path.exists(self.frames_file):
                self.get_logger().error(f"Frames file not found: {self.frames_file}")
                sys.exit(1)
            
            # Load frames from YAML
            with open(self.frames_file, 'r') as f:
                self.frames = yaml.safe_load(f)
        
        # Initialize publishers after frames are loaded
        self._initialize_publishers()
    
    def load_frames_from_warehouse(self):
        """Load frames from warehouse backup JSON file."""
        frames_file_path = os.path.join(os.path.expanduser('~/.ros/warehouse'), 'user_frames.json')
        
        if not os.path.exists(frames_file_path):
            self.get_logger().warn(f"Warehouse frames file not found: {frames_file_path}")
            self.get_logger().info("Try running 'ros2 run za6_moveit_config store_frames_to_warehouse.py' first")
            sys.exit(1)
        
        try:
            import json
            with open(frames_file_path, 'r') as f:
                frames_data = json.load(f)
            
            # Convert to YAML-like format for processing
            for frame_name, frame_def in frames_data.items():
                self.frames[frame_name] = {
                    'parent_frame': frame_def.get('parent_frame', 'world'),
                    'description': frame_def.get('description', '')
                }
                
                # Convert pose back to format expected by get_pose_from_frame_data
                if 'pose' in frame_def:
                    pose = frame_def['pose']
                    pos = pose['position']
                    orient = pose['orientation']
                    
                    # Convert quaternion to Euler
                    import math
                    qx, qy, qz, qw = orient['x'], orient['y'], orient['z'], orient['w']
                    
                    sinr_cosp = 2 * (qw * qx + qy * qz)
                    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
                    roll = math.atan2(sinr_cosp, cosr_cosp)
                    
                    sinp = 2 * (qw * qy - qz * qx)
                    if abs(sinp) >= 1:
                        pitch = math.copysign(math.pi / 2, sinp)
                    else:
                        pitch = math.asin(sinp)
                    
                    siny_cosp = 2 * (qw * qz + qx * qy)
                    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
                    yaw = math.atan2(siny_cosp, cosy_cosp)
                    
                    self.frames[frame_name]['pose'] = [
                        float(pos['x']),
                        float(pos['y']),
                        float(pos['z']),
                        float(roll),
                        float(pitch),
                        float(yaw)
                    ]
                
                # If joint_state source, preserve that
                if frame_def.get('source') == 'joint_state' and 'joint_state' in frame_def:
                    self.frames[frame_name]['joint_state'] = frame_def['joint_state']
                    if 'ee_link' in frame_def:
                        self.frames[frame_name]['ee_link'] = frame_def['ee_link']
            
            self.get_logger().info(f"Loaded {len(self.frames)} frames from warehouse")
            
        except Exception as e:
            self.get_logger().error(f"Failed to load frames from warehouse: {e}")
            sys.exit(1)
    
    def _initialize_publishers(self):
        """Initialize publishers (called after frames are loaded)."""
        # Publisher for markers
        self.marker_pub = self.create_publisher(MarkerArray, 'user_frames', 10)
        
        # FK service client (for joint-state frames)
        self.fk_client = self.create_client(GetPositionFK, 'compute_fk')
        self.fk_available = self.fk_client.wait_for_service(timeout_sec=2.0)
        if not self.fk_available:
            self.get_logger().warn("Forward kinematics service not available. Joint-state frames will be skipped.")
        
        # Default end effector link
        self.default_ee_link = 'grasp_link'
        
        # Timer to publish markers periodically
        self.timer = self.create_timer(1.0, self.publish_markers)
        
        if hasattr(self, 'frames_file'):
            self.get_logger().info(f"Loaded {len(self.frames)} frames from {self.frames_file}")
        else:
            self.get_logger().info(f"Loaded {len(self.frames)} frames from warehouse")
        self.get_logger().info("Publishing frame markers...")
    
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
    
    def rotate_vector_by_quaternion(self, vector, qx, qy, qz, qw):
        """Rotate a vector by a quaternion."""
        import math
        
        # Quaternion rotation: v' = q * v * q^-1
        # For unit quaternion, q^-1 = conjugate
        # v' = q * [0, vx, vy, vz] * [qw, -qx, -qy, -qz]
        vx, vy, vz = vector
        
        # Convert vector to quaternion (pure quaternion)
        v = [0.0, vx, vy, vz]
        
        # Quaternion multiplication: q * v
        qv_x = qw * v[1] + qy * v[3] - qz * v[2]
        qv_y = qw * v[2] + qz * v[1] - qx * v[3]
        qv_z = qw * v[3] + qx * v[2] - qy * v[1]
        qv_w = -qx * v[1] - qy * v[2] - qz * v[3]
        
        # Multiply by conjugate: result * [qw, -qx, -qy, -qz]
        result_x = qv_w * (-qx) + qv_x * qw + qv_y * (-qz) - qv_z * (-qy)
        result_y = qv_w * (-qy) + qv_y * qw + qv_z * (-qx) - qv_x * (-qz)
        result_z = qv_w * (-qz) + qv_z * qw + qv_x * (-qy) - qv_y * (-qx)
        
        return result_x, result_y, result_z
    
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
    
    def get_pose_from_frame_data(self, frame_name, frame_data):
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
            
            self.get_logger().debug(f"Computing forward kinematics for frame '{frame_name}' using {ee_link}")
            pose = self.compute_forward_kinematics(joint_names, joint_positions, ee_link)
            
            if pose is None:
                self.get_logger().error(f"Failed to compute FK for frame '{frame_name}'")
                return None, None
            
            return pose, parent_frame
        
        else:
            self.get_logger().warn(f"Frame {frame_name} has neither 'pose' nor 'joint_state'")
            return None, None
    
    def create_axis_markers(self, frame_name, pose, parent_frame, marker_id_base):
        """Create markers for x, y, z axes with different colors."""
        markers = []
        axis_length = 0.15  # 15cm arrows
        axis_radius = 0.01  # 1cm radius
        
        # Get frame position and orientation
        px, py, pz = pose.position.x, pose.position.y, pose.position.z
        qx, qy, qz, qw = pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w
        
        # Rotate local axis vectors by the frame's orientation
        # X axis in local frame: (1, 0, 0)
        x_vec = self.rotate_vector_by_quaternion((axis_length, 0.0, 0.0), qx, qy, qz, qw)
        # Y axis in local frame: (0, 1, 0)
        y_vec = self.rotate_vector_by_quaternion((0.0, axis_length, 0.0), qx, qy, qz, qw)
        # Z axis in local frame: (0, 0, 1)
        z_vec = self.rotate_vector_by_quaternion((0.0, 0.0, axis_length), qx, qy, qz, qw)
        
        # X axis marker (red)
        x_marker = Marker()
        x_marker.header.frame_id = parent_frame
        x_marker.header.stamp = self.get_clock().now().to_msg()
        x_marker.id = marker_id_base
        x_marker.type = Marker.ARROW
        x_marker.action = Marker.ADD
        
        # Scale for arrow
        x_marker.scale.x = axis_radius  # Shaft radius
        x_marker.scale.y = axis_radius * 1.5  # Head radius
        x_marker.scale.z = 0.0  # Not used for ARROW
        
        # Color (red for x-axis)
        x_marker.color.r = 1.0
        x_marker.color.g = 0.0
        x_marker.color.b = 0.0
        x_marker.color.a = 1.0
        
        # Arrow points: from origin to x axis direction
        x_marker.points.append(Point(x=px, y=py, z=pz))
        x_marker.points.append(Point(x=px + x_vec[0], y=py + x_vec[1], z=pz + x_vec[2]))
        
        x_marker.ns = f"{frame_name}_axes"
        markers.append(x_marker)
        
        # Y axis marker (green)
        y_marker = Marker()
        y_marker.header.frame_id = parent_frame
        y_marker.header.stamp = self.get_clock().now().to_msg()
        y_marker.id = marker_id_base + 1
        y_marker.type = Marker.ARROW
        y_marker.action = Marker.ADD
        
        y_marker.scale.x = axis_radius
        y_marker.scale.y = axis_radius * 1.5
        y_marker.scale.z = 0.0
        
        # Color (green for y-axis)
        y_marker.color.r = 0.0
        y_marker.color.g = 1.0
        y_marker.color.b = 0.0
        y_marker.color.a = 1.0
        
        y_marker.points.append(Point(x=px, y=py, z=pz))
        y_marker.points.append(Point(x=px + y_vec[0], y=py + y_vec[1], z=pz + y_vec[2]))
        
        y_marker.ns = f"{frame_name}_axes"
        markers.append(y_marker)
        
        # Z axis marker (blue)
        z_marker = Marker()
        z_marker.header.frame_id = parent_frame
        z_marker.header.stamp = self.get_clock().now().to_msg()
        z_marker.id = marker_id_base + 2
        z_marker.type = Marker.ARROW
        z_marker.action = Marker.ADD
        
        z_marker.scale.x = axis_radius
        z_marker.scale.y = axis_radius * 1.5
        z_marker.scale.z = 0.0
        
        # Color (blue for z-axis)
        z_marker.color.r = 0.0
        z_marker.color.g = 0.0
        z_marker.color.b = 1.0
        z_marker.color.a = 1.0
        
        z_marker.points.append(Point(x=px, y=py, z=pz))
        z_marker.points.append(Point(x=px + z_vec[0], y=py + z_vec[1], z=pz + z_vec[2]))
        
        z_marker.ns = f"{frame_name}_axes"
        markers.append(z_marker)
        
        # Optional: Add text label
        text_marker = Marker()
        text_marker.header.frame_id = parent_frame
        text_marker.header.stamp = self.get_clock().now().to_msg()
        text_marker.id = marker_id_base + 3
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD
        
        text_marker.pose.position.x = pose.position.x
        text_marker.pose.position.y = pose.position.y
        text_marker.pose.position.z = pose.position.z + axis_length + 0.02
        text_marker.pose.orientation.w = 1.0
        
        text_marker.scale.z = 0.05  # Text height
        text_marker.color.r = 1.0
        text_marker.color.g = 1.0
        text_marker.color.b = 1.0
        text_marker.color.a = 1.0
        text_marker.text = frame_name
        
        text_marker.ns = f"{frame_name}_axes"
        markers.append(text_marker)
        
        return markers
    
    def publish_markers(self):
        """Publish all frame markers."""
        marker_array = MarkerArray()
        marker_id = 0
        
        for frame_name, frame_data in self.frames.items():
            if not isinstance(frame_data, dict):
                continue
            
            # Get pose (from direct specification or computed from joint state)
            pose, parent_frame = self.get_pose_from_frame_data(frame_name, frame_data)
            
            if pose is None:
                continue
            
            # Create axis markers for this frame
            frame_markers = self.create_axis_markers(frame_name, pose, parent_frame, marker_id)
            marker_array.markers.extend(frame_markers)
            marker_id += 10  # Reserve space for each frame's markers
        
        # Publish marker array
        if len(marker_array.markers) > 0:
            self.marker_pub.publish(marker_array)
            self.get_logger().debug(f"Published {len(marker_array.markers)} markers for {len(self.frames)} frames")


def main(args=None):
    rclpy.init(args=args)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Publish user frames as visualization markers')
    parser.add_argument('--frames-file', type=str, help='Path to frames YAML file')
    parser.add_argument('--from-warehouse', action='store_true', help='Load frames from warehouse instead of YAML')
    args = parser.parse_args()
    
    publisher = FrameMarkerPublisher(frames_file=args.frames_file, load_from_warehouse=args.from_warehouse)
    
    try:
        rclpy.spin(publisher)
    except KeyboardInterrupt:
        pass
    
    publisher.destroy_node()
    rclpy.shutdown()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

