from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    ollama_model = LaunchConfiguration('ollama_model')
    ollama_url = LaunchConfiguration('ollama_url')

    return LaunchDescription([
        DeclareLaunchArgument('ollama_model', default_value='llama2.5'),
        DeclareLaunchArgument(
            'ollama_url', default_value='http://localhost:11434/api/chat'),

        Node(
            package='alpha_bot',
            executable='waypoint_teacher',
            name='waypoint_teacher',
            output='screen',
        ),
        Node(
            package='alpha_bot',
            executable='llm_commander',
            name='llm_commander',
            output='screen',
            parameters=[{
                'ollama_model': ollama_model,
                'ollama_url': ollama_url,
            }],
        ),
    ])
