from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # ------------------------------------------------------------------ args
    use_fake_hardware_arg = DeclareLaunchArgument(
        'use_fake_hardware', default_value='true',
        description='Use fake hardware (simulation) for both robots'
    )
    use_fake_hardware = LaunchConfiguration('use_fake_hardware')

    # ------------------------------------------------------------------ robot description
    # Resolve absolute paths for the melfa yaml configs (required by
    # rv5as_hardware macro which calls xacro.load_yaml() at parse time).
    melfa_description_share = FindPackageShare('melfa_description')
    melfa_initial_positions = PathJoinSubstitution(
        [melfa_description_share, 'config', 'initial_positions_rv.yaml']
    )
    melfa_controller_config = PathJoinSubstitution(
        [melfa_description_share, 'config', 'custom_io_params.yaml']
    )

    robot_description_content = Command([
        FindExecutable(name='xacro'), ' ',
        PathJoinSubstitution([
            FindPackageShare('vision_guided_dual_arm_main'),
            'urdf', 'dual_arm.urdf.xacro'
        ]),
        ' use_fake_hardware:=', use_fake_hardware,
        ' use_sim:=false',
        ' aubo_use_fake_hardware:=', use_fake_hardware,
        ' melfa_initial_positions_file:=', melfa_initial_positions,
        ' melfa_controller_config:=', melfa_controller_config,
    ])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    # ------------------------------------------------------------------ nodes
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            robot_description,
            PathJoinSubstitution([
                FindPackageShare('vision_guided_dual_arm_main'),
                'config', 'dual_arm_controllers.yaml'
            ]),
        ],
        output='screen',
    )

    # Spawners — each waits for the controller_manager to be available
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    melfa_jtc_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['melfa_joint_trajectory_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    aubo_jtc_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['aubo_joint_trajectory_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    # Start JTC spawners only after joint_state_broadcaster is active
    melfa_jtc_spawner_delayed = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[melfa_jtc_spawner],
        )
    )
    aubo_jtc_spawner_delayed = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[aubo_jtc_spawner],
        )
    )

    # rqt_joint_trajectory_controller — GUI for manually commanding joints
    rqt_joint_trajectory_controller = Node(
        package='rqt_joint_trajectory_controller',
        executable='rqt_joint_trajectory_controller',
        output='screen',
    )

    return LaunchDescription([
        use_fake_hardware_arg,
        robot_state_publisher,
        controller_manager,
        joint_state_broadcaster_spawner,
        melfa_jtc_spawner_delayed,
        aubo_jtc_spawner_delayed,
        rqt_joint_trajectory_controller,
    ])
