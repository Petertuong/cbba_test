"""Translate between ROS messages and the ROS-free cbba library objects."""
from geometry_msgs.msg import Point

from cbba.models import Message, Task
from cbba_interfaces.msg import CbbaMessage


def point_to_tuple(point):
    """ROS geometry_msgs/Point -> (x, y, z) tuple used by the cbba library."""
    return (point.x, point.y, point.z)


def tuple_to_point(position):
    """(x, y, z) tuple -> ROS geometry_msgs/Point.
    Refuses 2D input: a missing z would silently become 0.0 and hide a config mistake."""
    if len(position) != 3:
        raise ValueError('expected an (x, y, z) position, got %s' % (position,))
    x, y, z = position
    return Point(x=float(x), y=float(y), z=float(z))


def tasks_from_msg(task_array):
    tasks = {t.id: Task(t.id, point_to_tuple(t.position), t.static_score, t.discount_factor)
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
    out.sender_position = tuple_to_point(position)
    return out


def message_from_ros(ros_msg):
    return Message(ros_msg.sender_id,
                   list(ros_msg.winning_bids),
                   list(ros_msg.winning_agents),
                   list(ros_msg.timestamps))