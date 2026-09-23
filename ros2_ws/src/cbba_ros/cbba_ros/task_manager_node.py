"""Stand-in for the environment (later: Unity / the environment team).
Publishes the task list once, latched."""
from geometry_msgs.msg import Point
from rclpy.node import Node

from cbba_interfaces.msg import Task, TaskArray

from .qos import TASKS_QOS, TASKS_TOPIC
from .scenario import load_scenario
from .spin import spin_node


class TaskManagerNode(Node):

    def __init__(self):
        super().__init__('task_manager')
        path = self.declare_parameter('scenario_file', '').value
        scenario = load_scenario(path or None)

        msg = TaskArray()
        for t in scenario['tasks']:
            msg.tasks.append(Task(id=t['id'],
                                  position=Point(x=float(t['position'][0]),
                                                 y=float(t['position'][1])),
                                  static_score=float(t['static_score']),
                                  discount_factor=float(t['discount_factor'])))

        self.pub = self.create_publisher(TaskArray, TASKS_TOPIC, TASKS_QOS)
        self.pub.publish(msg)
        self.get_logger().info('published %d tasks on %s' % (len(msg.tasks), TASKS_TOPIC))


def main(args=None):
    spin_node(TaskManagerNode, args)


if __name__ == '__main__':
    main()
