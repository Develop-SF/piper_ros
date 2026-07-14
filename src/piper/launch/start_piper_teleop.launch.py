from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os

os.environ["RCUTILS_COLORIZED_OUTPUT"] = "1"   # 强制彩色日志

def generate_launch_description():
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level (debug, info, warn, error, fatal).'
    )
    # Declare the launch arguments
    can_leader_port_arg = DeclareLaunchArgument(
        'can_leader_port',
        default_value='piper_1',
        description='CAN leader port to be used by the Piper node.'
    )
    can_follower_port_arg = DeclareLaunchArgument(
        'can_follower_port',
        default_value='piper_2',
        description='CAN follower port to be used by the Piper node.'
    )

    auto_enable_arg = DeclareLaunchArgument(
        'auto_enable',
        default_value='true',
        description='Automatically enable the Piper node.'
    )
    
    rviz_ctrl_flag_arg = DeclareLaunchArgument(
        'rviz_ctrl_flag',
        default_value='false',
        description='Start rviz flag.'
    )
    
    girpper_exist_arg = DeclareLaunchArgument(
        'girpper_exist',
        default_value='true',
        description='gripper'
    )

    gripper_val_mutiple_arg = DeclareLaunchArgument(
        'gripper_val_mutiple',
        default_value='2',
        description='gripper'
    )

    # Define the node
    piper_leader_node = Node(
        package='piper',
        executable='piper_read_leader_joint',
        name='piper_leader_node',
        output='screen',
        ros_arguments=['--log-level', LaunchConfiguration('log_level')],
        parameters=[{
            'can_port': LaunchConfiguration('can_leader_port'),
            # 'auto_enable': LaunchConfiguration('auto_enable'),
            # 'rviz_ctrl_flag': LaunchConfiguration('rviz_ctrl_flag'),
            # 'girpper_exist': LaunchConfiguration('girpper_exist'),
            # 'gripper_val_mutiple': LaunchConfiguration('gripper_val_mutiple'),
        }],
        remappings=[
            # publisrh ctrl to follower
            ('joint_states', '/leader_joint_ctrl_cmd'),
        ]
    )

    piper_right_node = Node(
        package='piper',
        executable='piper_single_ctrl',
        name='piper_follower_node',
        output='screen',
        ros_arguments=['--log-level', LaunchConfiguration('log_level')],
        parameters=[{
            'can_port': LaunchConfiguration('can_follower_port'),
            'auto_enable': LaunchConfiguration('auto_enable'),
            'rviz_ctrl_flag': LaunchConfiguration('rviz_ctrl_flag'),
            'girpper_exist': LaunchConfiguration('girpper_exist'),
            'gripper_val_mutiple': LaunchConfiguration('gripper_val_mutiple'),
        }],
        remappings=[
            # subscribe ctrl from leader
            ('pos_cmd', '/pos_cmd_right'),
            ('joint_ctrl_single', '/leader_joint_ctrl_cmd'),
            # publish follower feedback
            ('joint_states_single', '/follower_joint_states'),
            ('joint_states_feedback', '/follower_joint'),
            ('joint_ctrl', '/follower_joint_states_ctrl'),
            ('arm_status', '/follower_arm_status'),
            ('end_pose', '/follower_end_pose'),
            ('end_pose_stamped', '/follower_end_pose_stamped'),
        ]
    )

    # Return the LaunchDescription
    return LaunchDescription([
        log_level_arg,
        can_leader_port_arg,
        can_follower_port_arg,
        auto_enable_arg,
        rviz_ctrl_flag_arg,
        girpper_exist_arg,
        gripper_val_mutiple_arg,
        piper_leader_node,
        piper_right_node,
    ])
