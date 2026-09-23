"""Global observer, for debugging only (no real agent has this view).

Listens to every consensus message and plan and reports whether the team
has reached a conflict-free agreement -- the same invariants as
tests/test_integration.py::test_convergence_invariants.
"""
from rclpy.node import Node

from cbba_interfaces.msg import AgentPlan, CbbaMessage

from .qos import CBBA_QOS, MESSAGES_TOPIC, PLANS_TOPIC
from .spin import spin_node


class MonitorNode(Node):

    def __init__(self):
        super().__init__('cbba_monitor')
        self.num_agents = self.declare_parameter('num_agents', 3).value
        self.z = {}      # agent id -> latest z_i
        self.plans = {}  # agent id -> latest AgentPlan
        self.reported = None

        self.create_subscription(CbbaMessage, MESSAGES_TOPIC, self.on_message, CBBA_QOS)
        self.create_subscription(AgentPlan, PLANS_TOPIC, self.on_plan, 10)
        self.create_timer(1.0, self.check)

    def on_message(self, msg):
        self.z[msg.sender_id] = list(msg.winning_agents)

    def on_plan(self, plan):
        self.plans[plan.agent_id] = plan

    def check(self):
        if len(self.z) < self.num_agents or len(self.plans) < self.num_agents:
            self.get_logger().info('waiting: heard from %d/%d agents'
                                   % (len(self.plans), self.num_agents))
            return

        problems = []
        zs = [tuple(z) for z in self.z.values()]
        if len(set(zs)) > 1:
            problems.append('agents disagree on z: %s' % dict(self.z))

        claimed = {}
        for a, plan in self.plans.items():
            for t in plan.bundle:
                claimed.setdefault(t, []).append(a)
        for t, owners in claimed.items():
            if len(owners) > 1:
                problems.append('task %d claimed by %s' % (t, owners))

        summary = ' | '.join('agent %d path=%s' % (a, list(self.plans[a].path))
                             for a in sorted(self.plans))
        state = (tuple(problems), summary)
        if state == self.reported:
            return
        self.reported = state
        if problems:
            self.get_logger().warn('NOT CONVERGED: ' + '; '.join(problems))
        else:
            self.get_logger().info('CONSENSUS z=%s  %s' % (list(zs[0]), summary))


def main(args=None):
    spin_node(MonitorNode, args)


if __name__ == '__main__':
    main()
