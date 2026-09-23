"""Start the task manager, one CBBA agent per entry in the scenario, and the monitor.

    ros2 launch cbba_ros cbba.launch.py
    ros2 launch cbba_ros cbba.launch.py scenario:=/path/to/other.yaml
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from cbba_ros.scenario import default_scenario_path, load_scenario


def make_nodes(context):
    path = LaunchConfiguration('scenario').perform(context)
    scenario = load_scenario(path)
    num_agents = len(scenario['agents'])

    nodes = [
        Node(package='cbba_ros', executable='task_manager', output='screen',
             parameters=[{'scenario_file': path}]),
        Node(package='cbba_ros', executable='monitor', output='screen',
             parameters=[{'num_agents': num_agents}]),
    ]
    for a in scenario['agents']:
        nodes.append(Node(
            package='cbba_ros', executable='agent', output='screen',
            namespace='agent_%d' % a['id'],
            parameters=[{
                'agent_id': a['id'],
                'num_agents': num_agents,
                'position': [float(v) for v in a['position']],
                'max_bundle': scenario['max_bundle'],
                'round_period': float(scenario['round_period']),
                'comm_range': float(scenario['comm_range']),
            }]))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value=default_scenario_path()),
        OpaqueFunction(function=make_nodes),
    ])
