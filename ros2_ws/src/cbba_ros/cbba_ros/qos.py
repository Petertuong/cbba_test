from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

# latched: an agent that starts late still receives the task list
TASKS_QOS = QoSProfile(depth=1,
                       reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)

CBBA_QOS = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)

TASKS_TOPIC = '/cbba/tasks'
MESSAGES_TOPIC = '/cbba/messages'
PLANS_TOPIC = '/cbba/plans'
