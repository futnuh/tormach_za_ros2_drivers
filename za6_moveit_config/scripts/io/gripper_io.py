#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers for toggling ZA6 gripper digital outputs."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from std_msgs.msg import Bool


@dataclass(frozen=True)
class DigitalOutputConfig:
    """Configuration for a HAL digital output channel."""

    command_topic: str = "/hal_io/dout01"
    feedback_topic: Optional[str] = "/hal_io/dout01"
    status_topic: Optional[str] = "/hal_io/digital_out_1"
    latch: bool = True


class DigitalOutputHelper:
    """Publish boolean commands to a HAL digital output with optional feedback."""

    def __init__(self, node: Node, config: Optional[DigitalOutputConfig] = None) -> None:
        if config is None:
            config = DigitalOutputConfig()
        self._node = node
        self._config = config
        qos = QoSProfile(depth=1)
        qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        self._publisher = node.create_publisher(Bool, config.command_topic, qos)
        self._status_publisher = (
            node.create_publisher(Bool, config.status_topic, qos)
            if config.status_topic
            else None
        )

        self._feedback_lock = threading.Lock()
        self._last_feedback: Optional[bool] = None
        self._feedback_subscriber = None

        if config.feedback_topic:
            self._feedback_subscriber = node.create_subscription(
                Bool, config.feedback_topic, self._feedback_callback, qos
            )

    def destroy(self) -> None:
        """Clean up ROS interfaces."""
        if self._feedback_subscriber is not None:
            self._node.destroy_subscription(self._feedback_subscriber)
            self._feedback_subscriber = None
        if self._publisher is not None:
            self._node.destroy_publisher(self._publisher)
            self._publisher = None

    def set(self, state: bool, wait_for_feedback: bool = False, timeout: float = 1.0) -> bool:
        """Command the digital output to the desired state."""
        msg = Bool()
        msg.data = state

        if not self._publisher:
            raise RuntimeError("DigitalOutputHelper publisher has been destroyed")

        self._publisher.publish(msg)
        if self._status_publisher:
            self._status_publisher.publish(msg)
        self._node.get_logger().debug(
            f"Published gripper command {state} to {self._config.command_topic}"
        )

        if not wait_for_feedback or not self._feedback_subscriber:
            return True

        return self._wait_for_feedback(state, timeout)

    def _feedback_callback(self, msg: Bool) -> None:
        with self._feedback_lock:
            self._last_feedback = msg.data

    def _wait_for_feedback(self, expected: bool, timeout: float) -> bool:
        """Spin until the commanded state is observed or timeout expires."""
        end_time = self._node.get_clock().now() + Duration(seconds=timeout)
        while self._node.get_clock().now() < end_time:
            with self._feedback_lock:
                if self._last_feedback == expected:
                    return True
            rclpy.spin_once(self._node, timeout_sec=0.05)

        with self._feedback_lock:
            current = self._last_feedback
        self._node.get_logger().warn(
            f"Timed out waiting for feedback on {self._config.feedback_topic}. "
            f"expected={expected} current={current}"
        )
        return False


class GripperController:
    """High-level helper to toggle the ZA6 gripper output."""

    def __init__(
        self,
        node: Node,
        open_is_true: bool = True,
        config: Optional[DigitalOutputConfig] = None,
    ) -> None:
        self._helper = DigitalOutputHelper(node, config=config)
        self._open_is_true = open_is_true

    def destroy(self) -> None:
        self._helper.destroy()

    def command_open(self, wait_for_feedback: bool = False, timeout: float = 1.0) -> bool:
        return self._helper.set(self._open_is_true, wait_for_feedback, timeout)

    def command_close(self, wait_for_feedback: bool = False, timeout: float = 1.0) -> bool:
        return self._helper.set(not self._open_is_true, wait_for_feedback, timeout)


