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
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import SwitchController


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
        
        # Servo control clients
        self.start_servo_client = self.create_client(Trigger, '/servo_node/start_servo')
        self.unpause_servo_client = self.create_client(Trigger, '/servo_node/unpause_servo')
        self.pause_servo_client = self.create_client(Trigger, '/servo_node/pause_servo')
        self.stop_servo_client = self.create_client(Trigger, '/servo_node/stop_servo')
        self.switch_controller_client = self.create_client(SwitchController, '/controller_manager/switch_controller')
        
        # Wait for services to be available (non-blocking, log warnings if not ready)
        self.get_logger().info('Checking for servo services...')
        if not self.start_servo_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('start_servo service not available')
        if not self.unpause_servo_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('unpause_servo service not available')
        if not self.pause_servo_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('pause_servo service not available')
        if not self.stop_servo_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('stop_servo service not available')
        if not self.switch_controller_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().warn('switch_controller service not available')
        
        # Subscriber
        self.joy_sub = self.create_subscription(
            Joy, '/joy', self.joy_callback, 10)
        
        self.get_logger().info('Gamepad to Servo converter initialized')
        self.get_logger().info('Press button 0 to enable servo, button 1 to disable')
        self.get_logger().info('Press bumper 4 for cartesian mode, bumper 5 for joint mode')
    
    def _call_service_async(self, client, service_name):
        """Helper method to call a service asynchronously."""
        if client.service_is_ready():
            request = Trigger.Request()
            future = client.call_async(request)
            future.add_done_callback(
                lambda f: self._service_callback(f, service_name)
            )
        else:
            self.get_logger().warn(f'Service {service_name} is not ready')
    
    def _service_callback(self, future, service_name):
        """Callback for service responses."""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Service {service_name} succeeded: {response.message}')
            else:
                self.get_logger().warn(f'Service {service_name} failed: {response.message}')
        except Exception as e:
            self.get_logger().error(f'Exception calling {service_name}: {str(e)}')

    def _switch_controllers(self, start: list[str], stop: list[str], strict: bool = True):
        """Asynchronously request controller switch via controller_manager (Humble API)."""
        if not self.switch_controller_client.service_is_ready():
            self.get_logger().warn('switch_controller service not ready')
            return
        req = SwitchController.Request()
        req.start_controllers = start
        req.stop_controllers = stop
        req.strictness = SwitchController.Request.STRICT if strict else SwitchController.Request.BEST_EFFORT
        self.switch_controller_client.call_async(req)
    
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
                self.get_logger().info(f'ENABLE button {enable_btn} pressed. Starting and unpausing servo...')
                # Try to start and unpause the servo - call start first, then unpause
                self._call_service_async(self.start_servo_client, 'start_servo')
                # Small delay to ensure start completes before unpause
                import time
                time.sleep(0.1)  # Brief delay
                self._call_service_async(self.unpause_servo_client, 'unpause_servo')
                # Switch controllers for teleop streaming
                self._switch_controllers(start=['streaming_controller'], stop=['joint_trajectory_controller'], strict=True)
        
        if len(msg.buttons) > disable_btn and msg.buttons[disable_btn] == 1:
            if not self.last_button_states.get(disable_btn, False):
                self.servo_enabled = False
                self.get_logger().info(f'DISABLE button {disable_btn} pressed. Pausing servo...')
                # Pause the servo when disabled
                self._call_service_async(self.pause_servo_client, 'pause_servo')
                # Switch controllers back for planning/execution
                self._switch_controllers(start=['joint_trajectory_controller'], stop=['streaming_controller'], strict=True)
        
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
        # Note: Triggers (axes 2, 5) read 1.0 when not pressed, -1.0 when fully pressed
        axes = []
        for i, axis in enumerate(msg.axes):
            # For triggers (axes 2 and 5), map from [1.0 (not pressed), -1.0 (pressed)] to [0.0, 1.0]
            if i in [2, 5]:  # Trigger axes
                # Map: 1.0 (not pressed) -> 0.0, -1.0 (pressed) -> 1.0
                # Formula: (1.0 - axis) / 2.0 maps [1.0, -1.0] to [0.0, 1.0]
                mapped_axis = (1.0 - axis) / 2.0
                # Apply deadzone - if below deadzone, set to 0.0
                if mapped_axis < deadzone:
                    axis = 0.0
                else:
                    # Keep as positive value [deadzone, 1.0] - triggers control positive rotation only
                    axis = mapped_axis
            else:
                # For regular axes (sticks), apply deadzone normally
                if abs(axis) < deadzone:
                    axis = 0.0
            axes.append(axis)
        
        # Debug: Log axis values and mode
        # Commented out to reduce log noise
        # has_movement = any(abs(a) >= deadzone for a in msg.axes)
        # if has_movement and len([a for a in axes if abs(a) >= 0.05]) > 0:
        #     mode = "CARTESIAN" if self.cartesian_mode else "JOINT"
        #     max_val = max([abs(a) for a in axes])
        #     self.get_logger().info(f"Publishing {mode} command, max axis: {max_val:.3f}")
        
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
        
        # Map axes to joint velocities (custom mapping for joint mode):
        # joint_1 <- axis 0 (left stick X)
        # joint_2 <- axis 1 (left stick Y)
        # joint_3 <- axis 3 (right stick X)
        # joint_4 <- axis 4 (right stick Y)
        # joint_5 <- axis -2 (second last axis)
        # joint_6 <- axis -1 (last axis)
        # Note: last two axes are discrete (-1, 0, +1) per user
        joint_cmd.velocities = [0.0] * 6

        # Safe getters
        def get_axis(idx: int) -> float:
            if -len(axes) <= idx < len(axes):
                return axes[idx]
            return 0.0

        joint_cmd.velocities[0] = get_axis(0) * max_joint
        joint_cmd.velocities[1] = get_axis(1) * max_joint
        # Swap: right stick Y -> joint_3, right stick X -> joint_4
        joint_cmd.velocities[2] = get_axis(4) * max_joint
        joint_cmd.velocities[3] = get_axis(3) * max_joint
        joint_cmd.velocities[4] = get_axis(-2) * max_joint
        joint_cmd.velocities[5] = get_axis(-1) * max_joint
        
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
