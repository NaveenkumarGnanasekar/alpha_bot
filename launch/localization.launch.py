import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_alpha_bot = get_package_share_directory('alpha_bot')

    # ---- Launch arguments ----
    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_alpha_bot, 'map', 'first_map.yaml'),
        description='Full path to map yaml file to load'
    )

    declare_params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_alpha_bot, 'config', 'nav2_params.yaml'),
        description='Full path to the nav2 params yaml file'
    )

    declare_use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )

    # ---- Nodes ----
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            params_file,
            {'use_sim_time': use_sim_time},
            {'yaml_filename': map_yaml_file},
        ]
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            params_file,
            {'use_sim_time': use_sim_time},
        ]
    )

 
    lifecycle_manager_node = Node(
    package='nav2_lifecycle_manager',
    executable='lifecycle_manager',
    name='lifecycle_manager_localization',
    output='screen',
    parameters=[{
        'use_sim_time': use_sim_time,
        'autostart': True,
        'node_names': [
            'map_server',
            'amcl'
        ]
    }]
)
    return LaunchDescription([
        declare_map_arg,
        declare_params_arg,
        declare_use_sim_time_arg,
        map_server_node,
        amcl_node,
        lifecycle_manager_node,
    ])