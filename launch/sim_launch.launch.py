import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess ,DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch.actions import SetEnvironmentVariable


def generate_launch_description():

    package_name = 'alpha_bot'

   
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory(package_name),
                'launch',
                'alpha.launch.py'
            )
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    world = os.path.join(get_package_share_directory(package_name),'urdf','empty_world.sdf')
    gazebo = ExecuteProcess(
    cmd=['gz', 'sim','-r',world],
    output='screen'
)
    
    rviz = ExecuteProcess(
        cmd=['rviz2'],
        output='screen'
    )

    # ================= SPAWN ROBOT =================
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'alpha_bot',
            '-z', '0.25'
        ],
        output='screen'
    )

    bridge_params = os.path.join(get_package_share_directory(package_name),'config','gz_bridge.yaml')
    ros_gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ]
    )
    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "diff_cont",
            '--controller-ros-args',
            '-r /diff_cont/cmd_vel:=/cmd_vel'
        ],
    )

    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_broad"],
    )
    twist_mux_config = os.path.join(get_package_share_directory(package_name),
                                         'config', 'twist_mux.yaml')
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        remappings={('/cmd_vel_out', '/cmd_vel_unstamped')},
        parameters=[
            {'use_sim_time': True},
            twist_mux_config])
    twist_stamper = Node(
    package='twist_stamper',
    executable='twist_stamper',
    parameters=[{'use_sim_time': True}, {'frame_id': 'base_link'}],
    remappings=[('/cmd_vel_in', '/cmd_vel_unstamped'),
                ('/cmd_vel_out', '/cmd_vel')],
)

    return LaunchDescription([
        rsp,
        gazebo,
        spawn_entity,
        rviz,
        ros_gz_bridge,
        diff_drive_spawner,
        joint_broad_spawner,
        twist_mux,
        twist_stamper,

        
    ])