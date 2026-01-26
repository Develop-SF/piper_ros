import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

class Robotis2Pipper(Node):
    def __init__(self):
        super().__init__('robotis2pipper')

        # last received msg snapshot
        self.latest_names = None
        self.latest_pos_by_name = {}  

        self.publisher_ = self.create_publisher(JointState, 'to_piper/joint_ctrl_single', 1)

        self.subscription = self.create_subscription(
            JointState,
            'from_robotis_leader/joint_states',
            self.listener_callback,
            1
        )

        timer_period = 1.0 / 200.0
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self._warned_missing = set()
        self._last_warn_time = 0.0


    def listener_callback(self, msg: JointState):
        if not msg.name or not msg.position:
            return

        n = min(len(msg.name), len(msg.position))
        names = list(msg.name[:n])
        poss = list(msg.position[:n])

        self.latest_names = names
        self.latest_pos_by_name = {names[i]: poss[i] for i in range(n)}

    def _get(self, suffix: str, default: float = 0.0) -> float:
        """
        Find a joint value by suffix match, e.g. suffix='joint6' matches 'ra_piper_joint6'.
        If not found, return default.
        """
        if not self.latest_pos_by_name:
            return default

        for k, v in self.latest_pos_by_name.items():
            if k.endswith(suffix):
                return float(v)

        # warn once per missing suffix
        if suffix not in self._warned_missing:
            self.get_logger().warning(f"Missing joint suffix '{suffix}' in input JointState.name")
            self._warned_missing.add(suffix)
        return default

    def timer_callback(self):
        if not self.latest_names or not self.latest_pos_by_name:
            now = self.get_clock().now().nanoseconds / 1e9
            if now - self._last_warn_time > 1.0:
                self.get_logger().warning('No valid joint state received yet.')
                self._last_warn_time = now
            return
            return

        # --- Read leader joints by NAME (order-independent) ---
        # Based on sample names: ...joint1..joint6 and ...rh_r1_joint
        L_j1 = self._get('joint1')
        L_j2 = self._get('joint2')
        L_j3 = self._get('joint3')
        L_j4 = self._get('joint4')
        L_j5 = self._get('joint5')
        L_j6 = self._get('joint6')
        L_gr = self._get('rh_r1_joint')  # gripper joint

        # --- Mapping logic (ported to name-based variables) ---
        # --- Duo to different joint order between Robotis and Piper, mapping as follows ---
        # leader joint1 -> piper joint1
        # leader joint2 -> piper joint2
        # leader joint3 -> piper joint3
        # leader joint4 -> piper joint5
        # leader joint5 -> piper joint4
        # leader joint6 -> piper joint6
        p_joint1 = max(-3.14, min(L_j1, 3.14))
        p_joint2 = max(0.0, min((L_j2 + 1.57), 2.618))
        p_joint3 = max(-2.618, min((L_j3 - 2.66), 0.0))
        p_joint4 = max(-1.7453, min((L_j5 - 1.57), 1.7453))
        p_joint5 = max(-1.2217, min((L_j4 + 1.57), 1.2217))
        p_joint6 = max(-1.7453, min(((L_j6 * -1.0) + 0.33), 1.7453))

        # leader gripper close~open: -0.8 ~ 0
        # piper gripper close~open: 0 ~ 0.035
        p_gripper = max(0.0, min(((L_gr + 0.8) * 0.04375), 0.035))

        # --- Build output message ---
        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'pipper_single'

        # IMPORTANT: output name order = input name order (keep identical)
        out.name = list(self.latest_names)

        # Now assign positions aligned with out.name[]
        out_pos = []
        for n in out.name:
            if n.endswith('joint1'):
                out_pos.append(p_joint1)
            elif n.endswith('joint2'):
                out_pos.append(p_joint2)
            elif n.endswith('joint3'):
                out_pos.append(p_joint3)
            elif n.endswith('joint4'):
                out_pos.append(p_joint4)
            elif n.endswith('joint5'):
                out_pos.append(p_joint5)
            elif n.endswith('joint6'):
                out_pos.append(p_joint6)
            elif n.endswith('rh_r1_joint'):
                out_pos.append(p_gripper)
            else:
                # If some extra name slips in, keep it 0.0
                out_pos.append(0.0)

        out.position = out_pos
        out.velocity = [100.0] * len(out.name)
        out.effort = [20.0] * len(out.name)

        self.publisher_.publish(out)
        self.get_logger().debug(f'Publishing positions (aligned): {out.position}')


def main(args=None):
    rclpy.init(args=args)
    node = Robotis2Pipper()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
