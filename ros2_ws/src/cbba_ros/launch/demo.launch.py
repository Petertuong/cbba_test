"""Visual demo: RViz + visualizer first, then the CBBA system a few seconds later.

    ros2 launch cbba_ros demo.launch.py
    ros2 launch cbba_ros demo.launch.py scenario:=/path/to/other.yaml
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('cbba_ros')

    # reuse the normal launch file (task manager + monitor + agents) instead of copying it
    cbba = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'cbba.launch.py')),
        launch_arguments={'scenario': LaunchConfiguration('scenario')}.items())

    return LaunchDescription([
        DeclareLaunchArgument('scenario',
                              default_value=os.path.join(share, 'config', 'demo.yaml')),
        Node(package='cbba_ros', executable='visualizer', output='screen'),
        Node(package='rviz2', executable='rviz2', output='log',
             arguments=['-d', os.path.join(share, 'rviz', 'cbba.rviz')]),
        # RViz takes a few seconds to open; start CBBA after it so you see round 1
        TimerAction(period=5.0, actions=[cbba]),
    ])
