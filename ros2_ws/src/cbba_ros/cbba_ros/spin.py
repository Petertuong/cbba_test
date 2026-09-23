import rclpy
from rclpy.executors import ExternalShutdownException


def spin_node(node_cls, args=None):
    """Run a node until Ctrl-C without the shutdown tracebacks rclpy prints
    when a second SIGINT lands during destroy_node()."""
    rclpy.init(args=args)
    try:
        rclpy.spin(node_cls())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        rclpy.try_shutdown()
