import os

from launch.event_handlers import OnProcessStart
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "prefix",
            default_value='',
            description="Joint/link prefix, e.g. la_piper_ or ra_piper_",
        ),
        DeclareLaunchArgument(
            'publish_robot_description_semantic',
            default_value='true',
            description='Whether to publish robot description semantic',
        ),
        DeclareLaunchArgument(
            "controller_spawner_timeout",
            default_value="60",
            description="Timeout used when spawning controllers.",
        ),
    ]

    prefix = LaunchConfiguration("prefix")
    publish_robot_description_semantic = LaunchConfiguration('publish_robot_description_semantic')
    controller_spawner_timeout = LaunchConfiguration(
        "controller_spawner_timeout"
    )

    ros2_controllers_path = PathJoinSubstitution(
        [
            FindPackageShare("piper_with_gripper_moveit"),
            "config",
            "ros2_controllers.yaml",
        ]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            ros2_controllers_path,
        ],
        remappings=[
            ("/controller_manager/robot_description", "/robot_description"),
        ],
        output="both",
    )

    # Spawn controllers
    def controller_spawner(controllers, active=True):
        inactive_flags = ["--inactive"] if not active else []
        return Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                *controllers,
                "--controller-manager",
                "/controller_manager",
                "--controller-manager-timeout",
                controller_spawner_timeout,
                *inactive_flags,
            ]
        )

    def build_spawn_actions(context, *args, **kwargs):
        prefix_value = context.perform_substitution(prefix)

        controllers_to_load = [
            f"{prefix_value}arm_controller",
            f"{prefix_value}gripper_controller",
            f"{prefix_value}joint_state_broadcaster",
        ]

        controller_spawners = controller_spawner(controllers_to_load, active=True)

        spawn_after_control = RegisterEventHandler(
            OnProcessStart(
                target_action=control_node,
                on_start=[controller_spawners],
            )
        )
        return [spawn_after_control]

    spawn_after_control = OpaqueFunction(function=build_spawn_actions)

    moveit_config = (
        MoveItConfigsBuilder("piper", package_name="piper_with_gripper_moveit")
        .robot_description(
            file_path="config/piper.urdf.xacro",
            mappings={"prefix": prefix},
        )
        .robot_description_semantic(
            file_path="config/piper.srdf.xacro",
            mappings={"prefix": prefix},
        )
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .to_moveit_configs()
    )

    # Start the actual move_group node/action server
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"publish_robot_description_semantic": publish_robot_description_semantic},
        ],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare('piper_with_gripper_moveit'), 'config', 'moveit.rviz']
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_moveit',
        output='log',
        arguments=['-d', rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    # Connect the robot to the world
    static_tf_pub = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=[
            "--x",
            "0.0",
            "--y",
            "0.0",
            "--z",
            "0.0",
            "--roll",
            "0.0",
            "--pitch",
            "0.0",
            "--yaw",
            "0.0",
            "--frame-id",
            "world",
            "--child-frame-id",
            [prefix, "base_link"],
        ],
    )

    # Publish TF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    return LaunchDescription(
        declared_arguments
        + [
            static_tf_pub,
            robot_state_publisher,
            control_node,
            spawn_after_control,
            move_group_node,
            rviz_node,
        ]
    )
