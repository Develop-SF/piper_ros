from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import os

os.environ["RCUTILS_COLORIZED_OUTPUT"] = "1"   # 强制彩色日志

def generate_launch_description():
    la_namespace_arg = DeclareLaunchArgument(
        'namespace_la',
        default_value='la_',
        description='ROS namespace for the node. e.g. la_ / ra_'
    )

    ra_namespace_arg = DeclareLaunchArgument(
        'namespace_ra',
        default_value='ra_',
        description='ROS namespace for the node. e.g. la_ / ra_'
    )

    # Define the node
    la_piper_node = Node(
        package='piper',
        executable='piper_read_robotis_joint',
        name='robotis_to_piper_node',
        namespace=LaunchConfiguration('namespace_la'),
        output='screen',
        remappings=[
            ('to_piper/joint_ctrl_single', '/la_piper_/joint_states'),
            ('from_robotis_leader/joint_states', '/la_robotis_as_piper_leader/joint_states'),
        ]
    )

    ra_piper_node = Node(
        package='piper',
        executable='piper_read_robotis_joint',
        name='robotis_to_piper_node',
        namespace=LaunchConfiguration('namespace_ra'),
        output='screen',
        remappings=[
            ('to_piper/joint_ctrl_single', '/ra_piper_/joint_states'),
            ('from_robotis_leader/joint_states', '/ra_robotis_as_piper_leader/joint_states'),
        ]
    )

    # Return the LaunchDescription
    return LaunchDescription([
        la_namespace_arg,
        ra_namespace_arg,
        la_piper_node,
        ra_piper_node
    ])
