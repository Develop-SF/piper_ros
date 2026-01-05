import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class Robotis2Pipper(Node):
    def __init__(self):
        super().__init__('robotis2pipper')

        self.latest_positions = [0.0, 1.57, -1.57, 0.0, 2.66, -1.57, 0.0, 0.0]  # initialize with default values

        self.publisher_ = self.create_publisher(JointState, 'to_piper/joint_ctrl_single', 1)

        self.subscription = self.create_subscription(
            JointState,
            'from_robotis_leader/joint_states',
            self.listener_callback,
            10
        )

        timer_period = 1.0 / 200.0
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def listener_callback(self, msg: JointState):
        positions = list(msg.position) if msg.position else []
        if len(positions) < 7:
            positions += [0.0] * (7 - len(positions))
        self.latest_positions = positions[:7]

    def timer_callback(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'pipper_single'
        msg.name = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'joint7']

        if (self.latest_positions[0] < -3.14) and \
            (self.latest_positions[1]< -3.14) and \
            (self.latest_positions[2]< -3.14) and \
            (self.latest_positions[3]< -3.14) and \
            (self.latest_positions[4]< -3.14) and \
            (self.latest_positions[5]< -3.14) and \
            (self.latest_positions[6]< -3.14):
            self.get_logger().warning('No valid joint positions received yet.')
            return
        
        joint1 = max(-1.7453, min((self.latest_positions[3]), 1.7453))  # TODO verify limits
        joint2 = max(0.0, min((self.latest_positions[5] + 1.57), 2.618)) 
        joint3 = max(-2.618, min((self.latest_positions[4] - 2.66), 0.0))
        joint4 = max(-1.7453, min((self.latest_positions[1] - 1.57), 1.7453))
        joint5 = max(-1.2217, min((self.latest_positions[2] + 1.57), 1.2217))
        joint6 = max(-1.7453, min(((self.latest_positions[0] * -1.0) + 0.33), 1.7453))
        # robotis close ~ open: -0.8 ~ 0
        # pipper close ~ open: 0 ~ 0.035
        gripper = max(0.0, min(((self.latest_positions[6] + 0.8) * 0.04375), 0.035))  # gripper = leader_right gripper * (0.035 / 0.8)

        msg.position = [
            joint1,
            joint2,
            joint3,
            joint4,
            joint5,
            joint6,
            gripper,
        ]
        # msg.position = self.latest_positions
        msg.velocity = [100.0] * 7
        msg.effort = [20.0] * 7

        self.publisher_.publish(msg)

        self.get_logger().debug(f'Publishing positions: {msg.position}')
        print(f'Publishing positions: {msg.position}')

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
