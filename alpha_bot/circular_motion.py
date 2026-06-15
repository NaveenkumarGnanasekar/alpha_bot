#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CircularMotionPublisher(Node):

    def __init__(self):
        super().__init__('circular_motion_publisher')

        self.publisher_ = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.timer = self.create_timer(0.1, self.publish_cmd_vel)

        self.get_logger().info('Publishing circular motion commands...')

    def publish_cmd_vel(self):
        msg = Twist()

        # Linear velocity (m/s)
        msg.linear.x = 0.3

        # Angular velocity (rad/s)
        msg.angular.z = 0.5

        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = CircularMotionPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    # Stop the robot before exiting
    stop_msg = Twist()
    node.publisher_.publish(stop_msg)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()