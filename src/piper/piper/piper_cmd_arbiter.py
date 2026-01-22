#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Piper Arbiter Node (ROS 2, rclpy)

Arbitrates between:
  1) teleop leader input topic (sensor_msgs/JointState)
  2) moveit input topic (sensor_msgs/JointState)

Mode is switched via a SetBool service:
  - True  => forward teleop
  - False => forward moveit

Selected stream is republished to output_topic for piper driver node to consume.
"""

import time
from typing import Optional, Tuple

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from std_srvs.srv import SetBool


class JointStateArbiter(Node):
    def __init__(self):
        super().__init__('piper_jointstate_arbiter')

        # ---- Parameters ----
        self.declare_parameter('teleop_topic', 'teleop_joint_cmd')   # JointState
        self.declare_parameter('moveit_topic', 'moveit_joint_cmd')   # JointState
        self.declare_parameter('output_topic', 'joint_ctrl_single')  # JointState (to piper driver)

        # Service name to switch mode: std_srvs/SetBool
        self.declare_parameter('mode_service', 'set_teleop_enabled')

        # If selected source becomes stale, optionally fall back to the other source.
        # Set 0.0 to disable fallback.
        self.declare_parameter('stale_timeout_sec', 0.0)

        # Publish rate for forwarding (0 = publish immediately on input callbacks)
        self.declare_parameter('publish_rate_hz', 0.0)

        self.teleop_topic = self.get_parameter('teleop_topic').value
        self.moveit_topic = self.get_parameter('moveit_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.mode_service = self.get_parameter('mode_service').value
        self.stale_timeout_sec = float(self.get_parameter('stale_timeout_sec').value)
        self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)

        # ---- State ----
        self.enable_teleop: bool = False  # default: moveit
        self.last_teleop_msg: Optional[JointState] = None
        self.last_moveit_msg: Optional[JointState] = None
        self.last_teleop_rx: float = 0.0
        self.last_moveit_rx: float = 0.0

        # ---- Pub/Sub ----
        self.pub = self.create_publisher(JointState, self.output_topic, 1)
        self.create_subscription(JointState, self.teleop_topic, self._teleop_cb, 1)
        self.create_subscription(JointState, self.moveit_topic, self._moveit_cb, 1)

        # ---- Service ----
        self.srv = self.create_service(SetBool, self.mode_service, self._set_mode_srv_cb)

        # Optional periodic publisher
        if self.publish_rate_hz > 0.0:
            self.create_timer(1.0 / self.publish_rate_hz, self._timer_publish)

        self.get_logger().info(
            "JointState Arbiter started.\n"
            f"  teleop_topic:     {self.teleop_topic}\n"
            f"  moveit_topic:     {self.moveit_topic}\n"
            f"  output_topic:     {self.output_topic}\n"
            f"  mode_service:     {self.mode_service} (std_srvs/SetBool)\n"
            f"  stale_timeout_sec:{self.stale_timeout_sec}\n"
            f"  publish_rate_hz:  {self.publish_rate_hz}\n"
            f"  initial mode:     {'teleop' if self.enable_teleop else 'moveit'}"
        )

    def _now(self) -> float:
        return time.time()

    def _teleop_cb(self, msg: JointState):
        self.last_teleop_msg = msg
        self.last_teleop_rx = self._now()
        if self.publish_rate_hz <= 0.0:
            self._forward_if_selected()

    def _moveit_cb(self, msg: JointState):
        self.last_moveit_msg = msg
        self.last_moveit_rx = self._now()
        if self.publish_rate_hz <= 0.0:
            self._forward_if_selected()

    def _set_mode_srv_cb(self, request: SetBool.Request, response: SetBool.Response):
        prev = self.enable_teleop
        self.enable_teleop = bool(request.data)

        if prev != self.enable_teleop:
            self.get_logger().info(f"Mode changed: {prev} -> {self.enable_teleop} "
                                   f"({'teleop' if self.enable_teleop else 'moveit'})")

        # Try to publish immediately from newly selected source (if available)
        ok, detail = self._forward_if_selected(force=True)

        response.success = True
        response.message = (
            f"mode={'teleop' if self.enable_teleop else 'moveit'}; "
            f"forward={ok}; {detail}"
        )
        return response

    def _is_stale(self, last_rx: float) -> bool:
        if self.stale_timeout_sec <= 0.0:
            return False
        return (self._now() - last_rx) > self.stale_timeout_sec

    def _select_source(self) -> Tuple[Optional[JointState], str]:
        teleop_ok = (self.last_teleop_msg is not None) and (not self._is_stale(self.last_teleop_rx))
        moveit_ok = (self.last_moveit_msg is not None) and (not self._is_stale(self.last_moveit_rx))

        if self.enable_teleop:
            if teleop_ok:
                return self.last_teleop_msg, "teleop"
            if moveit_ok:
                return self.last_moveit_msg, "moveit(fallback)"
            return None, "none"
        else:
            if moveit_ok:
                return self.last_moveit_msg, "moveit"
            if teleop_ok:
                return self.last_teleop_msg, "teleop(fallback)"
            return None, "none"

    def _forward_if_selected(self, force: bool = False) -> Tuple[bool, str]:
        msg, src = self._select_source()
        if msg is None:
            if force:
                self.get_logger().warn("No valid input to forward (selected source missing or stale).")
            return False, "no valid input (missing/stale)"

        self.pub.publish(msg)
        if force:
            self.get_logger().info(f"Forwarded one message from: {src}")
        return True, f"forwarded from {src}"

    def _timer_publish(self):
        self._forward_if_selected(force=False)


def main(args=None):
    rclpy.init(args=args)
    node = JointStateArbiter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

