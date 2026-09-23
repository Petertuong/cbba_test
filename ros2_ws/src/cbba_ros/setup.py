from glob import glob

from setuptools import setup

package_name = 'cbba_ros'

setup(
    name=package_name,
    version='0.1.0',
    # `cbba` is a symlink to the ROS-free algorithm at the repo root
    packages=[package_name, 'cbba'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Petertuong',
    maintainer_email='tuong.bin2103@gmail.com',
    description='ROS 2 nodes running the Consensus-Based Bundle Algorithm',
    license='MIT',
    entry_points={
        'console_scripts': [
            'agent = cbba_ros.agent_node:main',
            'task_manager = cbba_ros.task_manager_node:main',
            'monitor = cbba_ros.monitor_node:main',
            'visualizer = cbba_ros.visualizer_node:main',
        ],
    },
)
