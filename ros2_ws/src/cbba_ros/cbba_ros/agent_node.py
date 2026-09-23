"""One CBBA agent. Each timer tick is one CBBA round:

    consume inbox -> release -> build bundle -> broadcast

which is the same phase order as cbba/main.py, just started from a
different point of the cycle.
"""
from geometry_msgs.msg import Point
from rclpy.node import Node

from cbba.bundle import build_bundle
from cbba.consensus import consume_message, produce_message, release
from cbba.geometry import euclidean_distance
from cbba.models import Agent
from cbba_interfaces.msg import AgentPlan, CbbaMessage, TaskArray

from .conversions import message_from_ros, message_to_ros, tasks_from_msg
from .qos import CBBA_QOS, MESSAGES_TOPIC, PLANS_TOPIC, TASKS_QOS, TASKS_TOPIC
from .spin import spin_node


class CbbaAgentNode(Node):

    def __init__(self):
        super().__init__('cbba_agent')
        self.agent_id = self.declare_parameter('agent_id', 0).value
        self.num_agents = self.declare_parameter('num_agents', 3).value
        self.position = tuple(self.declare_parameter('position', [0.0, 0.0]).value)
        self.max_bundle = self.declare_parameter('max_bundle', 2).value
        self.comm_range = self.declare_parameter('comm_range', -1.0).value
        round_period = self.declare_parameter('round_period', 0.5).value

        self.agent = None       # created once tasks are known
        self.tasks = None
        self.inbox = []
        self.stable_rounds = 0

        self.create_subscription(TaskArray, TASKS_TOPIC, self.on_tasks, TASKS_QOS)
        self.create_subscription(CbbaMessage, MESSAGES_TOPIC, self.on_message, CBBA_QOS)
        self.msg_pub = self.create_publisher(CbbaMessage, MESSAGES_TOPIC, CBBA_QOS)
        self.plan_pub = self.create_publisher(AgentPlan, PLANS_TOPIC, 10)
        self.create_timer(round_period, self.on_round)

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

    def on_round(self):
        if self.agent is None:
            return
        agent = self.agent
        before = (list(agent.bundle), list(agent.winning_agent_list))

        # phase 2 (for messages received since last tick)
        inbox, self.inbox = self.inbox, []
        for m in inbox:
            consume_message(agent, m)
        release(agent)

        # phase 1
        build_bundle(agent, self.tasks, self.max_bundle)

        # s_ik only ever compares values stamped by the same agent m, so each
        # agent's own monotonic clock is enough; no cross-machine sync needed.
        now = self.get_clock().now().nanoseconds * 1e-9
        msg = produce_message(agent, now)
        self.msg_pub.publish(message_to_ros(msg, self.position))

        after = (list(agent.bundle), list(agent.winning_agent_list))
        if after == before:
            self.stable_rounds += 1
        else:
            self.stable_rounds = 0
            self.get_logger().info('bundle=%s path=%s z=%s'
                                   % (agent.bundle, agent.path, agent.winning_agent_list))
        self.publish_plan()

    # -------------------------------------------------------------- helpers

    def in_range(self, sender_position):
        if self.comm_range < 0:
            return True
        return euclidean_distance(self.position,
                                  (sender_position.x, sender_position.y)) <= self.comm_range

    def publish_plan(self):
        plan = AgentPlan()
        plan.agent_id = self.agent_id
        plan.bundle = list(self.agent.bundle)
        plan.path = list(self.agent.path)
        plan.waypoints = [Point(x=float(self.tasks[t].position[0]),
                                y=float(self.tasks[t].position[1])) for t in self.agent.path]
        plan.stable_rounds = self.stable_rounds
        self.plan_pub.publish(plan)


def main(args=None):
    spin_node(CbbaAgentNode, args)


if __name__ == '__main__':
    main()
