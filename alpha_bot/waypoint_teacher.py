import os
import math

import yaml
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class WaypointTeacher(Node):


    def __init__(self):
        super().__init__('waypoint_teacher')

        self.declare_parameter(
            'waypoints_file',
            os.path.expanduser('~/alpha_bot_llm_nav/waypoints.yaml'),
        )
        self.waypoints_file = self.get_parameter(
            'waypoints_file').get_parameter_value().string_value
        os.makedirs(os.path.dirname(self.waypoints_file), exist_ok=True)

        self.current_pose = None

        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self.pose_cb, 10)
        self.create_subscription(
            String, '/save_waypoint', self.save_cb, 10)

        self.get_logger().info(
            f'Waypoint teacher ready. Saving to {self.waypoints_file}')
        self.get_logger().info(
            "Publish a name to /save_waypoint to remember the robot's "
            "current pose, e.g.:")
        self.get_logger().info(
            "  ros2 topic pub -1 /save_waypoint std_msgs/String "
            "\"data: 'kitchen'\"")

    def pose_cb(self, msg):
        self.current_pose = msg.pose.pose

    def save_cb(self, msg):
        name = msg.data.strip()
        if not name:
            return
        if self.current_pose is None:
            self.get_logger().warn(
                'No /amcl_pose received yet, cannot save waypoint')
            return

        waypoints = {}
        if os.path.exists(self.waypoints_file):
            with open(self.waypoints_file, 'r') as f:
                waypoints = yaml.safe_load(f) or {}

        p = self.current_pose
        waypoints[name] = {
            'x': float(p.position.x),
            'y': float(p.position.y),
            'yaw': float(yaw_from_quaternion(p.orientation)),
        }

        with open(self.waypoints_file, 'w') as f:
            yaml.safe_dump(waypoints, f)

        self.get_logger().info(
            f"Saved waypoint '{name}' at "
            f"x={waypoints[name]['x']:.2f}, "
            f"y={waypoints[name]['y']:.2f}, "
            f"yaw={waypoints[name]['yaw']:.2f}")


def main():
    rclpy.init()
    node = WaypointTeacher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
