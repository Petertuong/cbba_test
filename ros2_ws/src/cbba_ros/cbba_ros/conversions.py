"""Translate between ROS messages and the ROS-free cbba library objects."""
from geometry_msgs.msg import Point

from cbba.models import Message, Task
from cbba_interfaces.msg import CbbaMessage


def tasks_from_msg(task_array):
    tasks = {t.id: Task(t.id, (t.position.x, t.position.y), t.static_score, t.discount_factor)
             for t in task_array.tasks}
    if sorted(tasks) != list(range(len(tasks))):
        raise ValueError('task ids must be 0..N-1, got %s' % sorted(tasks))
    return tasks


def message_to_ros(msg, position):
    out = CbbaMessage()
    out.sender_id = msg.sender_id
    out.winning_bids = [float(v) for v in msg.winning_bid_list]
    out.winning_agents = [int(v) for v in msg.winning_agent_list]
    out.timestamps = [float(v) for v in msg.timestamp_list]
    out.sender_position = Point(x=float(position[0]), y=float(position[1]))
    return out


def message_from_ros(ros_msg):
    return Message(ros_msg.sender_id,
                   list(ros_msg.winning_bids),
                   list(ros_msg.winning_agents),
                   list(ros_msg.timestamps))