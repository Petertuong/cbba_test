"""One CBBA agent. Each round:

    consume inbox -> release -> build bundle -> broadcast

which is the same phase order as cbba/main.py, just started from a
different point of the cycle.

Rounds are SYNCHRONOUS, as in the paper and the offline simulator:
  * round r starts at the same wall-clock instant for every agent
    (r = clock time // round_period), so agents need a shared clock
    (true on one machine; across machines use NTP/chrony);
  * a message sent in round r is only used in round r+1, even if it
    arrives earlier. So in round 1 every agent bids without knowing the
    others' bids, and the conflicts are resolved in the next round.
"""
from rclpy.node import Node

from cbba.bundle import build_bundle
from cbba.consensus import consume_message, produce_message, release
from cbba.geometry import euclidean_distance
from cbba.models import Agent
from cbba_interfaces.msg import AgentPlan, CbbaMessage, TaskArray

from .conversions import (message_from_ros, message_to_ros, point_to_tuple,
                          tasks_from_msg, tuple_to_point)
from .qos import CBBA_QOS, MESSAGES_TOPIC, PLANS_TOPIC, TASKS_QOS, TASKS_TOPIC
from .spin import spin_node


class CbbaAgentNode(Node):

    def __init__(self):
        super().__init__('cbba_agent')
        self.agent_id = self.declare_parameter('agent_id', 0).value
        self.num_agents = self.declare_parameter('num_agents', 3).value
        self.position = tuple(self.declare_parameter('position', [0.0, 0.0, 0.0]).value)  # (x, y, z)
        if len(self.position) != 3:
            raise ValueError('position must be [x, y, z], got %s' % (self.position,))
        self.max_bundle = self.declare_parameter('max_bundle', 2).value
        self.comm_range = self.declare_parameter('comm_range', -1.0).value
        self.round_period = self.declare_parameter('round_period', 0.5).value

        self.agent = None       # created once tasks are known
        self.tasks = None
        self.inbox = []
        self.stable_rounds = 0
        self.current_round = None  # number of the round we last ran
        self.first_round = None    # first round we take part in (set when tasks arrive)

        self.create_subscription(TaskArray, TASKS_TOPIC, self.on_tasks, TASKS_QOS)
        self.create_subscription(CbbaMessage, MESSAGES_TOPIC, self.on_message, CBBA_QOS)
        self.msg_pub = self.create_publisher(CbbaMessage, MESSAGES_TOPIC, CBBA_QOS)
        self.plan_pub = self.create_publisher(AgentPlan, PLANS_TOPIC, 10)
        # check the clock often (20 Hz) and run a round whenever a new one begins,
        # instead of "every round_period since I started", which differs per agent
        self.create_timer(0.05, self.on_clock)

        self.get_logger().info('agent %d at %s, waiting for tasks on %s'
                               % (self.agent_id, self.position, TASKS_TOPIC))

    # ------------------------------------------------------------ callbacks

    def on_tasks(self, task_array):
        tasks = tasks_from_msg(task_array)
        if self.agent is not None:
            # Assumption 1: the task set is static. Dynamic tasks are a later step.
            # (A latched topic can legitimately deliver the same list twice.)
            if set(tasks) != set(self.tasks):
                self.get_logger().warn('task list changed; ignoring (static task assumption)')
            return
        self.tasks = tasks
        self.agent = Agent(self.agent_id, self.position, len(self.tasks), self.num_agents)
        # start at the NEXT round boundary, not in the middle of the current round:
        # all agents that get the tasks during the same round then start together
        now = self.get_clock().now().nanoseconds * 1e-9
        self.first_round = int(now // self.round_period) + 1
        self.get_logger().info('received %d tasks, starting CBBA' % len(self.tasks))

    def on_message(self, ros_msg):
        if self.agent is None or ros_msg.sender_id == self.agent_id:
            return
        if len(ros_msg.winning_agents) != len(self.tasks):
            self.get_logger().error('message from %d has %d tasks, expected %d'
                                    % (ros_msg.sender_id, len(ros_msg.winning_agents),
                                       len(self.tasks)))
            return
        if not self.in_range(ros_msg.sender_position):
            return
        self.inbox.append(message_from_ros(ros_msg))

    def on_clock(self):
        # every agent computes the same round number from the same clock
        now = self.get_clock().now().nanoseconds * 1e-9
        rnd = int(now // self.round_period)
        if rnd != self.current_round:
            self.current_round = rnd
            self.on_round(rnd)

    def on_round(self, rnd):
        if self.agent is None or rnd < self.first_round:
            return
        agent = self.agent
        before = (list(agent.bundle), list(agent.winning_agent_list))

        # phase 2, only for messages sent in EARLIER rounds. The sender stamps
        # its own entry with its round number (produce_message), so that entry
        # tells us when the message was sent. Messages from this round stay in
        # the inbox until the next round.
        ready = [m for m in self.inbox if m.timestamp_list[m.sender_id] < rnd]
        self.inbox = [m for m in self.inbox if m.timestamp_list[m.sender_id] >= rnd]
        for m in ready:
            consume_message(agent, m)
        release(agent)

        # phase 1
        build_bundle(agent, self.tasks, self.max_bundle)

        # timestamps are round numbers, exactly as in the offline simulator
        msg = produce_message(agent, rnd)
        self.msg_pub.publish(message_to_ros(msg, self.position))

        after = (list(agent.bundle), list(agent.winning_agent_list))
        if after == before:
            self.stable_rounds += 1
        else:
            self.stable_rounds = 0
            # rnd is huge (seconds since 1970 / period); the last 3 digits are
            # enough to line up the logs of different agents
            self.get_logger().info('round %03d: bundle=%s path=%s z=%s'
                                   % (rnd % 1000, agent.bundle, agent.path,
                                      agent.winning_agent_list))
        self.publish_plan()

    # -------------------------------------------------------------- helpers

    def in_range(self, sender_position):
        if self.comm_range < 0:
            return True
        # 3D distance: a difference in height counts toward the range too
        return euclidean_distance(self.position, point_to_tuple(sender_position)) <= self.comm_range

    def publish_plan(self):
        plan = AgentPlan()
        plan.agent_id = self.agent_id
        plan.bundle = list(self.agent.bundle)
        plan.path = list(self.agent.path)
        plan.waypoints = [tuple_to_point(self.tasks[t].position) for t in self.agent.path]
        plan.stable_rounds = self.stable_rounds
        self.plan_pub.publish(plan)


def main(args=None):
    spin_node(CbbaAgentNode, args)


if __name__ == '__main__':
    main()
