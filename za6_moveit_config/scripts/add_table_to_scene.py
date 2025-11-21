#!/usr/bin/env python3
"""
Script to add RobotTable models to the MoveIt planning scene.
Loads both:
- RobotTableCollisionVolume.obj: Low-poly model for MoveIt collision checking
- RobotTableVisualizationModel.obj: High-res model for RViz visualization

Both models are pre-positioned and oriented in world space.
Can be run while the robot stack is running to test the table placement.
"""

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject, PlanningScene, ObjectColor
from visualization_msgs.msg import Marker, MarkerArray
from shape_msgs.msg import Mesh, MeshTriangle
from geometry_msgs.msg import Pose, Point
from std_msgs.msg import Header, ColorRGBA
from builtin_interfaces.msg import Duration
import os
import sys


def load_obj_file(obj_path):
    """
    Load an OBJ file and convert it to a shape_msgs/Mesh message.
    Returns (vertices, triangles) where vertices is a list of (x,y,z) tuples
    and triangles is a list of (i1, i2, i3) vertex index tuples.
    """
    vertices = []
    triangles = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            if parts[0] == 'v':  # Vertex
                if len(parts) >= 4:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                    vertices.append((x, y, z))
            
            elif parts[0] == 'f':  # Face
                # OBJ faces can have 3+ vertices, we'll triangulate
                # For now, assume triangular faces
                if len(parts) >= 4:
                    # OBJ indices are 1-based, convert to 0-based
                    # Handle format: "f v1 v2 v3" or "f v1/vt1 v2/vt2 v3/vt3"
                    face_indices = []
                    for part in parts[1:4]:  # Take first 3 vertices
                        # Handle "v/vt/vn" format by taking first number
                        idx_str = part.split('/')[0]
                        try:
                            idx = int(idx_str) - 1  # Convert to 0-based
                            if idx < 0:
                                idx = len(vertices) + idx  # Handle negative indices
                            face_indices.append(idx)
                        except ValueError:
                            continue
                    
                    if len(face_indices) == 3:
                        triangles.append(tuple(face_indices))
    
    return vertices, triangles


def create_mesh_collision_object(obj_path, object_id, frame_id="world", pose=None, scale=(1.0, 1.0, 1.0)):
    """
    Create a CollisionObject message from an OBJ file.
    
    Args:
        obj_path: Path to the OBJ file
        object_id: Name/ID for the collision object
        frame_id: Frame in which to place the object (default: "world")
        pose: geometry_msgs/Pose for the object (default: identity at origin)
        scale: Tuple (x, y, z) scaling factors (default: (1.0, 1.0, 1.0))
    
    Returns:
        moveit_msgs/msg/CollisionObject
    """
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"OBJ file not found: {obj_path}")
    
    # Load OBJ file
    vertices, triangles = load_obj_file(obj_path)
    
    if not vertices:
        raise ValueError(f"No vertices found in OBJ file: {obj_path}")
    if not triangles:
        raise ValueError(f"No faces found in OBJ file: {obj_path}")
    
    # Create CollisionObject message
    collision_object = CollisionObject()
    collision_object.header = Header()
    collision_object.header.frame_id = frame_id
    collision_object.header.stamp = rclpy.clock.Clock().now().to_msg()
    collision_object.id = object_id
    collision_object.operation = CollisionObject.ADD
    
    # Set pose (default to identity at origin)
    if pose is None:
        pose = Pose()
        pose.orientation.w = 1.0
    collision_object.pose = pose
    
    # Create mesh message
    mesh = Mesh()
    
    # Add vertices (apply scaling)
    for v in vertices:
        point = Point()
        point.x = v[0] * scale[0]
        point.y = v[1] * scale[1]
        point.z = v[2] * scale[2]
        mesh.vertices.append(point)
    
    # Add triangles
    for tri in triangles:
        triangle = MeshTriangle()
        triangle.vertex_indices = list(tri)
        mesh.triangles.append(triangle)
    
    collision_object.meshes = [mesh]
    # mesh_poses is relative to collision_object.pose, so identity is fine
    from geometry_msgs.msg import Pose as PoseMsg
    mesh_pose = PoseMsg()
    mesh_pose.orientation.w = 1.0
    collision_object.mesh_poses = [mesh_pose]
    
    return collision_object


class TableAdder(Node):
    def __init__(self):
        super().__init__('add_table_to_scene')
        self.planning_scene_publisher = self.create_publisher(
            PlanningScene,
            '/planning_scene',
            10
        )
        self.marker_publisher = self.create_publisher(
            MarkerArray,
            '/visualization_marker_array',
            10
        )
        self.get_logger().info("Table adder node initialized")
    
    def wait_for_planning_scene(self, timeout_sec=15.0):
        """Wait for planning scene to be available"""
        import time
        
        self.get_logger().info("Waiting for planning scene to be ready...")
        # Wait for at least one subscriber to /planning_scene (MoveIt/RViz)
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            subscriber_count = self.planning_scene_publisher.get_subscription_count()
            if subscriber_count > 0:
                self.get_logger().info(f"Planning scene subscriber detected (count: {subscriber_count})")
                return True
            elapsed = time.time() - start_time
            if int(elapsed) % 2 == 0 and elapsed > 0.5:  # Log every 2 seconds
                self.get_logger().info(f"Still waiting for planning scene subscriber... ({elapsed:.1f}s elapsed)")
            rclpy.spin_once(self, timeout_sec=0.5)
        
        self.get_logger().warn(f"Timeout waiting for planning scene subscriber after {timeout_sec}s, publishing anyway")
        return False
    
    def add_collision_object(self, collision_object, transparent=False):
        """Publish collision object to the planning scene"""
        planning_scene = PlanningScene()
        planning_scene.is_diff = True
        planning_scene.world.collision_objects = [collision_object]
        
        # Make collision object transparent if requested (invisible but still used for collision checking)
        if transparent:
            object_color = ObjectColor()
            object_color.id = collision_object.id
            object_color.color = ColorRGBA()
            object_color.color.r = 0.0
            object_color.color.g = 0.0
            object_color.color.b = 0.0
            object_color.color.a = 0.0  # Fully transparent
            planning_scene.object_colors = [object_color]
        
        self.planning_scene_publisher.publish(planning_scene)
        self.get_logger().info(f"Published collision object: {collision_object.id} (transparent={transparent})")
    
    def add_visualization_marker(self, obj_path, marker_id="robot_table_visual", frame_id="world", pose=None):
        """Publish visualization marker (non-collision) for RViz display"""
        marker = Marker()
        marker.header = Header()
        marker.header.frame_id = frame_id
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "robot_table"
        marker.id = 0
        marker.type = Marker.MESH_RESOURCE
        marker.action = Marker.ADD
        
        # Set pose
        if pose is None:
            pose = Pose()
            pose.orientation.w = 1.0
        marker.pose = pose
        
        # Set mesh resource (use file:// URL for absolute path)
        marker.mesh_resource = f"file://{obj_path}"
        marker.mesh_use_embedded_materials = True
        
        # Scale (1.0 means use mesh as-is)
        marker.scale.x = 1.0
        marker.scale.y = 1.0
        marker.scale.z = 1.0
        
        # Color (will be overridden by embedded materials if mesh_use_embedded_materials is True)
        marker.color.r = 0.7
        marker.color.g = 0.7
        marker.color.b = 0.7
        marker.color.a = 1.0
        
        # Lifetime (0 = never delete)
        marker.lifetime = Duration()
        marker.lifetime.sec = 0
        marker.lifetime.nanosec = 0
        
        marker_array = MarkerArray()
        marker_array.markers = [marker]
        
        self.marker_publisher.publish(marker_array)
        self.get_logger().info(f"Published visualization marker from: {obj_path}")


def main(args=None):
    # Initialize ROS 2 - handle both direct execution and ros2 run
    if args is None:
        args = sys.argv
    rclpy.init(args=args)
    
    # Filter out ROS 2 arguments to find user-provided OBJ file path
    user_args = []
    skip_next = False
    for arg in sys.argv[1:]:  # Skip script name
        if skip_next:
            skip_next = False
            continue
        if arg in ['--ros-args', '-r', '--params-file']:
            skip_next = True  # Skip the next argument (value for these flags)
            continue
        if arg.startswith('__node:=') or arg.startswith('--'):
            continue  # Skip ROS 2 remapping and other flags
        user_args.append(arg)

    # Default paths - use package share directory under meshes/edm
    try:
        share_dir = get_package_share_directory("za6_moveit_config")
    except Exception:
        share_dir = ""
    mesh_dir = os.path.join(share_dir, "meshes", "edm")
    collision_obj_path = os.path.join(mesh_dir, "RobotTableCollisionVolume.obj")
    visual_obj_path = os.path.join(mesh_dir, "RobotTableVisualizationModel.obj")

    # Fallback: check workspace root
    if not os.path.exists(collision_obj_path):
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        collision_obj_path = os.path.join(workspace_root, "RobotTableCollisionVolume.obj")
        visual_obj_path = os.path.join(workspace_root, "RobotTableVisualizationModel.obj")
    
    # Allow override via command line (for backward compatibility)
    if len(user_args) > 0:
        collision_obj_path = user_args[0]
        visual_obj_path = user_args[0]
    
    if not os.path.exists(collision_obj_path):
        print(f"Error: Collision OBJ file not found: {collision_obj_path}")
        print(f"Usage: {sys.argv[0]} [path_to_RobotTableCollisionVolume.obj]")
        return 1
    
    if not os.path.exists(visual_obj_path):
        print(f"Warning: Visualization OBJ file not found: {visual_obj_path}")
        print("Will use collision model for visualization as well.")
        visual_obj_path = None
    
    try:
        # Models are pre-positioned and oriented, so use identity pose
        from geometry_msgs.msg import Pose
        table_pose = Pose()
        table_pose.position.x = 0.0
        table_pose.position.y = 0.0
        table_pose.position.z = 0.0
        table_pose.orientation.w = 1.0  # Identity quaternion
        
        # Collision object pose: shift down 0.001m in z
        collision_pose = Pose()
        collision_pose.position.x = 0.0
        collision_pose.position.y = 0.0
        collision_pose.position.z = -0.001  # Shifted down 0.001m
        collision_pose.orientation.w = 1.0
        
        # No scaling needed - models are already in correct units
        scale = (1.0, 1.0, 1.0)
        
        # Create collision object (for MoveIt collision checking)
        collision_object = create_mesh_collision_object(
            collision_obj_path,
            object_id="robot_table",
            frame_id="world",
            pose=collision_pose,
            scale=scale
        )
        
        # Create node and publish
        node = TableAdder()
        
        try:
            # Wait for planning scene to be ready (MoveIt/RViz may not be up yet)
            node.wait_for_planning_scene(timeout_sec=15.0)
            
            # Small delay to ensure everything is ready
            rclpy.spin_once(node, timeout_sec=0.5)
            
            # Publish collision object to planning scene (make it transparent so visualization marker shows through)
            node.get_logger().info("Publishing collision object...")
            node.add_collision_object(collision_object, transparent=True)
            
            # Give it a moment to publish
            rclpy.spin_once(node, timeout_sec=0.5)
            
            # Publish visualization marker (non-collision) if available
            # Keep visualization at original position (no z offset)
            if visual_obj_path:
                node.get_logger().info("Publishing visualization marker...")
                node.add_visualization_marker(
                    visual_obj_path,
                    marker_id="robot_table_visual",
                    frame_id="world",
                    pose=table_pose
                )
                # Give it a moment to publish
                rclpy.spin_once(node, timeout_sec=0.5)
            
            if visual_obj_path:
                node.get_logger().info("✓ Table added successfully! Collision object for planning, visualization marker for display (non-collision).")
            else:
                node.get_logger().info("✓ Table collision model added successfully! Check RViz to see it.")
            
            # Keep node alive briefly to ensure messages are sent
            rclpy.spin_once(node, timeout_sec=1.0)
            
        except Exception as e:
            node.get_logger().error(f"Error adding table: {e}")
            import traceback
            traceback.print_exc()
        finally:
            node.destroy_node()
            rclpy.shutdown()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

