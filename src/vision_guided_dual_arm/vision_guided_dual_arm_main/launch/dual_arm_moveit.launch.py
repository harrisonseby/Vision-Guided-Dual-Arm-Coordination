import os
import yaml

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def load_file(package_name, file_path):
    abs_path = os.path.join(get_package_share_directory(package_name), file_path)
    with open(abs_path, 'r') as f:
        return f.read()


def load_yaml(package_name, file_path):
    abs_path = os.path.join(get_package_share_directory(package_name), file_path)
    with open(abs_path, 'r') as f:
        return yaml.safe_load(f)


def generate_launch_description():

    pkg = 'vision_guided_dual_arm_main'

    # ------------------------------------------------------------------ args
    use_fake_hardware_arg = DeclareLaunchArgument(
        'use_fake_hardware', default_value='true',
        description='Use fake hardware (simulation) for both robots'
    )
    use_fake_hardware = LaunchConfiguration('use_fake_hardware')

    # ------------------------------------------------------------------ robot description (URDF via xacro)
    melfa_description_share = FindPackageShare('melfa_description')
    melfa_initial_positions = PathJoinSubstitution(
        [melfa_description_share, 'config', 'initial_positions_rv.yaml']
    )
    melfa_controller_config = PathJoinSubstitution(
        [melfa_description_share, 'config', 'custom_io_params.yaml']
    )

    robot_description_content = Command([
        FindExecutable(name='xacro'), ' ',
        PathJoinSubstitution([FindPackageShare(pkg), 'urdf', 'dual_arm.urdf.xacro']),
        ' use_fake_hardware:=', use_fake_hardware,
        ' use_sim:=false',
        ' aubo_use_fake_hardware:=', use_fake_hardware,
        ' melfa_initial_positions_file:=', melfa_initial_positions,
        ' melfa_controller_config:=', melfa_controller_config,
    ])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    # ------------------------------------------------------------------ semantic description (SRDF)
    robot_description_semantic = {
        'robot_description_semantic': load_file(pkg, 'config/dual_arm.srdf')
    }

    # ------------------------------------------------------------------ kinematics
    kinematics_yaml = load_yaml(pkg, 'config/kinematics.yaml')

    # ------------------------------------------------------------------ joint limits
    joint_limits_yaml = {
        'robot_description_planning': load_yaml(pkg, 'config/joint_limits.yaml')
    }

    # ------------------------------------------------------------------ OMPL planning pipeline
    ompl_planning_yaml = load_yaml(pkg, 'config/ompl_planning.yaml')
    ompl_planning_pipeline_config = {
        'move_group': {
            'planning_plugin': 'ompl_interface/OMPLPlanner',
            'request_adapters': (
                'default_planner_request_adapters/AddTimeOptimalParameterization '
                'default_planner_request_adapters/ResolveConstraintFrames '
                'default_planner_request_adapters/FixWorkspaceBounds '
                'default_planner_request_adapters/FixStartStateBounds '
                'default_planner_request_adapters/FixStartStateCollision '
                'default_planner_request_adapters/FixStartStatePathConstraints'
            ),
            'start_state_max_bounds_error': 0.1,
        }
    }
    ompl_planning_pipeline_config['move_group'].update(ompl_planning_yaml)

    # ------------------------------------------------------------------ MoveIt controllers
    moveit_controllers = {
        'moveit_simple_controller_manager': load_yaml(pkg, 'config/moveit_controllers.yaml'),
        'moveit_controller_manager': (
            'moveit_simple_controller_manager/MoveItSimpleControllerManager'
        ),
    }

    trajectory_execution = {
        'moveit_manage_controllers': False,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.05,
    }

    planning_scene_monitor_parameters = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
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
            PathJoinSubstitution([FindPackageShare(pkg), 'config', 'dual_arm_controllers.yaml']),
        ],
        output='screen',
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    melfa_jtc_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['melfa_joint_trajectory_controller', '--controller-manager', '/controller_manager'],
        output='screen',
    )

    aubo_jtc_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['aubo_joint_trajectory_controller', '--controller-manager', '/controller_manager'],
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

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            robot_description,
            robot_description_semantic,
            kinematics_yaml,
            ompl_planning_pipeline_config,
            trajectory_execution,
            moveit_controllers,
            planning_scene_monitor_parameters,
            joint_limits_yaml,
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='log',
        arguments=[
            '-d', PathJoinSubstitution([FindPackageShare(pkg), 'rviz', 'dual_arm_moveit.rviz'])
        ],
        parameters=[
            robot_description,
            robot_description_semantic,
            ompl_planning_pipeline_config,
            kinematics_yaml,
            joint_limits_yaml,
        ],
    )

    return LaunchDescription([
        use_fake_hardware_arg,
        robot_state_publisher,
        controller_manager,
        joint_state_broadcaster_spawner,
        melfa_jtc_spawner_delayed,
        aubo_jtc_spawner_delayed,
        move_group_node,
        rviz_node,
    ])
