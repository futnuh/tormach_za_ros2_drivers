#!/usr/bin/env python3

# Copyright (c) 2023 Tormach, Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the {copyright_holder} nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import TwistStamped, Twist
from std_msgs.msg import Float64MultiArray
from control_msgs.msg import JointJog


class GamepadToServo(Node):
    """Convert gamepad input to MoveIt Servo commands."""
    
    def __init__(self):
        super().__init__('gamepad_to_servo')
        
        # Parameters
        self.declare_parameter('deadzone', 0.1)
        self.declare_parameter('max_linear_speed', 0.1)
        self.declare_parameter('max_angular_speed', 0.5)
        self.declare_parameter('max_joint_speed', 0.5)
        
        # Button mappings
        self.declare_parameter('enable_servo_button', 0)
        self.declare_parameter('disable_servo_button', 1)
        self.declare_parameter('cartesian_mode_button', 4)
        self.declare_parameter('joint_mode_button', 5)
        
        # Axis mappings
        self.declare_parameter('linear_x_axis', 1)
        self.declare_parameter('linear_y_axis', 0)
        self.declare_parameter('linear_z_axis', 4)
        self.declare_parameter('angular_x_axis', 3)
        self.declare_parameter('angular_y_axis', 2)
        self.declare_parameter('angular_z_axis', 5)
        
        # State variables
        self.servo_enabled = False
        self.cartesian_mode = True
        self.last_button_states = {}
        
        # Publishers - Note: servo node listens to these topics (with namespace)
        self.cartesian_pub = self.create_publisher(
            TwistStamped, '/servo_node/delta_twist_cmds', 10)
        self.joint_pub = self.create_publisher(
            JointJog, '/servo_node/delta_joint_cmds', 10)
        
        # Subscriber
        self.joy_sub = self.create_subscription(
            Joy, '/joy', self.joy_callback, 10)
        
        self.get_logger().info('Gamepad to Servo converter initialized')
        self.get_logger().info('Press button 0 to enable servo, button 1 to disable')
        self.get_logger().info('Press bumper 4 for cartesian mode, bumper 5 for joint mode')
    
    def joy_callback(self, msg):
        """Process gamepad input and convert to servo commands."""
        
        # Get parameters
        deadzone = self.get_parameter('deadzone').value
        max_linear = self.get_parameter('max_linear_speed').value
        max_angular = self.get_parameter('max_angular_speed').value
        max_joint = self.get_parameter('max_joint_speed').value
        
        # Button mappings
        enable_btn = self.get_parameter('enable_servo_button').value
        disable_btn = self.get_parameter('disable_servo_button').value
        cartesian_btn = self.get_parameter('cartesian_mode_button').value
        joint_btn = self.get_parameter('joint_mode_button').value
        
        # Handle button presses
        if len(msg.buttons) > enable_btn and msg.buttons[enable_btn] == 1:
            if not self.last_button_states.get(enable_btn, False):
                self.servo_enabled = True
                self.get_logger().info('Servo ENABLED')
        
        if len(msg.buttons) > disable_btn and msg.buttons[disable_btn] == 1:
            if not self.last_button_states.get(disable_btn, False):
                self.servo_enabled = False
                self.get_logger().info('Servo DISABLED')
        
        if len(msg.buttons) > cartesian_btn and msg.buttons[cartesian_btn] == 1:
            if not self.last_button_states.get(cartesian_btn, False):
                self.cartesian_mode = True
                self.get_logger().info('Switched to CARTESIAN mode')
        
        if len(msg.buttons) > joint_btn and msg.buttons[joint_btn] == 1:
            if not self.last_button_states.get(joint_btn, False):
                self.cartesian_mode = False
                self.get_logger().info('Switched to JOINT mode')
        
        # Update button states
        for i, pressed in enumerate(msg.buttons):
            self.last_button_states[i] = pressed
        
        # Only send commands if servo is enabled
        if not self.servo_enabled:
            return
        
        # Apply deadzone to axes
        axes = []
        for axis in msg.axes:
            if abs(axis) < deadzone:
                axes.append(0.0)
            else:
                axes.append(axis)
        
        # Debug: Log axis values and mode
        has_movement = any(abs(a) >= deadzone for a in msg.axes)
        if has_movement and len([a for a in axes if abs(a) >= 0.05]) > 0:
            mode = "CARTESIAN" if self.cartesian_mode else "JOINT"
            max_val = max([abs(a) for a in axes])
            self.get_logger().info(f"Publishing {mode} command, max axis: {max_val:.3f}")
        
        if self.cartesian_mode:
            self.send_cartesian_command(axes, max_linear, max_angular)
        else:
            self.send_joint_command(axes, max_joint)
    
    def send_cartesian_command(self, axes, max_linear, max_angular):
        """Send cartesian motion command."""
        twist = TwistStamped()
        twist.header.stamp = self.get_clock().now().to_msg()
        twist.header.frame_id = "tool0"
        
        # Map axes to linear and angular velocities
        linear_x_axis = self.get_parameter('linear_x_axis').value
        linear_y_axis = self.get_parameter('linear_y_axis').value
        linear_z_axis = self.get_parameter('linear_z_axis').value
        angular_x_axis = self.get_parameter('angular_x_axis').value
        angular_y_axis = self.get_parameter('angular_y_axis').value
        angular_z_axis = self.get_parameter('angular_z_axis').value
        
        if linear_x_axis < len(axes):
            twist.twist.linear.x = axes[linear_x_axis] * max_linear
        if linear_y_axis < len(axes):
            twist.twist.linear.y = axes[linear_y_axis] * max_linear
        if linear_z_axis < len(axes):
            twist.twist.linear.z = axes[linear_z_axis] * max_linear
            
        if angular_x_axis < len(axes):
            twist.twist.angular.x = axes[angular_x_axis] * max_angular
        if angular_y_axis < len(axes):
            twist.twist.angular.y = axes[angular_y_axis] * max_angular
        if angular_z_axis < len(axes):
            twist.twist.angular.z = axes[angular_z_axis] * max_angular
        
        self.cartesian_pub.publish(twist)
    
    def send_joint_command(self, axes, max_joint):
        """Send joint motion command."""
        joint_cmd = JointJog()
        joint_cmd.header.stamp = self.get_clock().now().to_msg()
        joint_cmd.header.frame_id = "world"
        
        # Joint names (adjust based on your robot)
        joint_cmd.joint_names = [
            'joint_1', 'joint_2', 'joint_3', 
            'joint_4', 'joint_5', 'joint_6'
        ]
        
        # Map axes to joint velocities
        joint_cmd.velocities = []
        for i in range(min(6, len(axes))):
            joint_cmd.velocities.append(axes[i] * max_joint)
        
        # Pad with zeros if needed
        while len(joint_cmd.velocities) < 6:
            joint_cmd.velocities.append(0.0)
        
        self.joint_pub.publish(joint_cmd)


def main(args=None):
    rclpy.init(args=args)
    node = GamepadToServo()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
