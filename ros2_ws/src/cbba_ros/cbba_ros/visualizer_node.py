"""Draws the live CBBA state in RViz. A debug tool, like the monitor: it
listens to every agent, which no real agent could do.

Listens to:
    /cbba/tasks     task positions
    /cbba/messages  agent positions (sender_position) and each agent's bids (y)
    /cbba/plans     each agent's bundle and path
Publishes:
    /cbba/markers   visualization_msgs/MarkerArray, redrawn 5 times per second

What you see:
    sphere          an agent, one colour per agent
    cube            a task: grey = unclaimed, agent colour = claimed,
                    red = CONFLICT (two agents both have it in their bundle)
    line            an agent's path: from the agent through its tasks in visit order
"""
from geometry_msgs.msg import Point
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray

from cbba_interfaces.msg import AgentPlan, CbbaMessage, TaskArray

from .qos import CBBA_QOS, MESSAGES_TOPIC, PLANS_TOPIC, TASKS_QOS, TASKS_TOPIC
from .spin import spin_node

MARKERS_TOPIC = '/cbba/markers'
FRAME = 'map'  # the coordinate frame markers are drawn in; RViz's "Fixed Frame" must match

# (r, g, b) between 0 and 1. One colour per agent id, reused if there are more agents.
AGENT_COLOURS = [(0.2, 0.4, 1.0), (1.0, 0.55, 0.1), (0.2, 0.8, 0.3), (0.7, 0.3, 0.9)]
UNCLAIMED = (0.6, 0.6, 0.6)
CONFLICT = (1.0, 0.0, 0.0)
WHITE = (1.0, 1.0, 1.0)

# sizes in world units (the scenario uses coordinates in the hundreds)
AGENT_SIZE = 40.0
TASK_SIZE = 30.0
LINE_WIDTH = 6.0
TEXT_HEIGHT = 25.0
LABEL_OFFSET = 50.0  # labels float this far above the object


def rgba(rgb, alpha=1.0):
    return ColorRGBA(r=rgb[0], g=rgb[1], b=rgb[2], a=alpha)


def agent_colour(agent_id):
    return AGENT_COLOURS[agent_id % len(AGENT_COLOURS)]


def above(point, offset):
    return Point(x=point.x, y=point.y, z=point.z + offset)


class VisualizerNode(Node):

    def __init__(self):
        super().__init__('cbba_visualizer')
        # latest known state, filled in by the callbacks below
        self.tasks = {}   # task id  -> Point
        self.agents = {}  # agent id -> Point (from the agent's last message)
        self.bids = {}    # agent id -> list of bids (that agent's view of y)
        self.plans = {}   # agent id -> AgentPlan

        # same QoS as the agents use, otherwise the subscriptions don't match
        self.create_subscription(TaskArray, TASKS_TOPIC, self.on_tasks, TASKS_QOS)
        self.create_subscription(CbbaMessage, MESSAGES_TOPIC, self.on_message, CBBA_QOS)
        self.create_subscription(AgentPlan, PLANS_TOPIC, self.on_plan, 10)

        self.pub = self.create_publisher(MarkerArray, MARKERS_TOPIC, 10)
        # redraw on a timer instead of in every callback: 5 Hz is smooth enough
        # and keeps the drawing code in one place
        self.create_timer(0.2, self.draw)

    # ------------------------------------------------------------ callbacks
    # They only store the data; draw() turns it into pictures.

    def on_tasks(self, task_array):
        self.tasks = {t.id: t.position for t in task_array.tasks}

    def on_message(self, msg):
        self.agents[msg.sender_id] = msg.sender_position
        self.bids[msg.sender_id] = list(msg.winning_bids)

    def on_plan(self, plan):
        self.plans[plan.agent_id] = plan

    # -------------------------------------------------------------- drawing

    def draw(self):
        out = MarkerArray()

        # who claims each task, according to each agent's OWN bundle
        claimers = {}  # task id -> [agent ids]
        for agent_id, plan in self.plans.items():
            for t in plan.bundle:
                claimers.setdefault(t, []).append(agent_id)

        for agent_id, pos in self.agents.items():
            out.markers.append(self.shape(Marker.SPHERE, 'agents', agent_id, pos,
                                          AGENT_SIZE, agent_colour(agent_id)))
            out.markers.append(self.text('agent_labels', agent_id,
                                         above(pos, LABEL_OFFSET), 'agent %d' % agent_id))

        for task_id, pos in self.tasks.items():
            owners = claimers.get(task_id, [])
            if not owners:
                colour, label = UNCLAIMED, 'task %d' % task_id
            elif len(owners) == 1:
                colour = agent_colour(owners[0])
                label = 'task %d\nbid %.2e' % (task_id, self.bid(owners[0], task_id))
            else:
                colour, label = CONFLICT, 'task %d\nCONFLICT %s' % (task_id, owners)
            out.markers.append(self.shape(Marker.CUBE, 'tasks', task_id, pos, TASK_SIZE, colour))
            out.markers.append(self.text('task_labels', task_id, above(pos, LABEL_OFFSET), label))

        for agent_id, plan in self.plans.items():
            out.markers.append(self.path_line(agent_id, plan))

        self.pub.publish(out)

    def bid(self, agent_id, task_id):
        bids = self.bids.get(agent_id, [])
        return bids[task_id] if task_id < len(bids) else 0.0

    # ------------------------------------------------------ marker builders

    def base(self, kind, ns, marker_id):
        """Fields every marker needs. (ns, id) names a marker: publishing the
        same (ns, id) again REPLACES it in RViz instead of adding a new one."""
        m = Marker()
        m.header.frame_id = FRAME
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = ns
        m.id = marker_id
        m.type = kind
        m.action = Marker.ADD
        m.pose.orientation.w = 1.0  # "no rotation"; an all-zero quaternion is invalid
        return m

    def shape(self, kind, ns, marker_id, position, size, colour):
        m = self.base(kind, ns, marker_id)
        m.pose.position = position
        m.scale.x = m.scale.y = m.scale.z = size
        m.color = rgba(colour)
        return m

    def text(self, ns, marker_id, position, label):
        m = self.base(Marker.TEXT_VIEW_FACING, ns, marker_id)  # always faces the camera
        m.pose.position = position
        m.scale.z = TEXT_HEIGHT  # for text only scale.z matters: the letter height
        m.color = rgba(WHITE)
        m.text = label
        return m

    def path_line(self, agent_id, plan):
        m = self.base(Marker.LINE_STRIP, 'paths', agent_id)
        start = self.agents.get(agent_id)
        if start is None or not plan.waypoints:
            m.action = Marker.DELETE  # nothing to draw: remove any old line
            return m
        m.points = [start] + list(plan.waypoints)  # agent -> task -> task ...
        m.scale.x = LINE_WIDTH  # for lines only scale.x matters: the width
        m.color = rgba(agent_colour(agent_id), alpha=0.8)
        return m


def main(args=None):
    spin_node(VisualizerNode, args)


if __name__ == '__main__':
    main()
