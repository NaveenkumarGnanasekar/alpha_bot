import os
import json
import math

import yaml
import requests
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose, NavigateThroughPoses


SYSTEM_PROMPT_TEMPLATE = """You are the command interpreter for a mobile \
robot running ROS2 Nav2.
You convert a user's natural language instruction into a single JSON \
object describing what to do. Output ONLY the JSON object, nothing else.

Known locations (name -> approximate pose the robot can navigate to):
{locations}

JSON schema:
{{
  "action": "navigate_to_pose" | "navigate_through_poses" | "save_waypoint" | "cancel" | "unknown",
  "waypoints": ["location_name", ...],
  "new_name": "name",
  "message": "a short natural-language reply to the user"
}}

Rules:
- "waypoints" is used for navigate_to_pose (exactly one name) and
  navigate_through_poses (an ordered list of two or more names). Every
  name MUST come from the known locations list above.
- If the user refers to a place that is NOT in the known locations list,
  set action to "unknown" and explain in "message" that you don't know
  that location, and list the known location names.
- If the user says something like "remember this place as X" or
  "this is the kitchen" or "save this spot as X", set action to
  "save_waypoint" with "new_name" set to X.
- If the user wants to stop, cancel, or abort the current motion, set
  action to "cancel".
- If the instruction is unrelated to navigation or unclear, set action
  to "unknown" with a helpful "message".
- Always include a short "message" field, even for navigation actions
  (e.g. "Heading to the kitchen now.").
"""


def yaw_to_quaternion(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class LLMCommander(Node):
    """
    Subscribes to /user_command (std_msgs/String), sends the instruction
    plus the known-waypoints list to a local Ollama model, and acts on
    the structured JSON response: sends Nav2 NavigateToPose /
    NavigateThroughPoses goals, triggers waypoint saving, or cancels
    the active goal.
    """

    def __init__(self):
        super().__init__('llm_commander')

        self.declare_parameter(
            'waypoints_file',
            os.path.expanduser('~/alpha_bot_llm_nav/waypoints.yaml'))
        self.declare_parameter('ollama_url', 'http://localhost:11434/api/chat')
        self.declare_parameter('ollama_model', 'llama3.1')
        self.declare_parameter('map_frame', 'map')

        self.waypoints_file = self.get_parameter(
            'waypoints_file').get_parameter_value().string_value
        self.ollama_url = self.get_parameter(
            'ollama_url').get_parameter_value().string_value
        self.ollama_model = self.get_parameter(
            'ollama_model').get_parameter_value().string_value
        self.map_frame = self.get_parameter(
            'map_frame').get_parameter_value().string_value

        self.create_subscription(
            String, '/user_command', self.command_cb, 10)
        self.save_pub = self.create_publisher(String, '/save_waypoint', 10)

        self.nav_to_pose_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose')
        self.nav_through_poses_client = ActionClient(
            self, NavigateThroughPoses, 'navigate_through_poses')

        self._goal_handle = None
        self._active_client = None

        self.get_logger().info(
            'LLM commander ready. Listening on /user_command.')
        self.get_logger().info(
            f'Using Ollama model "{self.ollama_model}" at {self.ollama_url}')

  
    def load_waypoints(self):
        if not os.path.exists(self.waypoints_file):
            return {}
        with open(self.waypoints_file, 'r') as f:
            return yaml.safe_load(f) or {}

    def query_llm(self, user_text, waypoints):
        if waypoints:
            locations = '\n'.join(
                f'- {name}: x={d["x"]:.2f}, y={d["y"]:.2f}, '
                f'yaw={d["yaw"]:.2f}'
                for name, d in waypoints.items()
            )
        else:
            locations = '(none saved yet)'

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(locations=locations)

        payload = {
            'model': self.ollama_model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_text},
            ],
            'format': 'json',
            'stream': False,
        }

        try:
            resp = requests.post(self.ollama_url, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()['message']['content']
            return json.loads(content)
        except Exception as e:
            self.get_logger().error(f'LLM query failed: {e}')
            return {'action': 'unknown', 'message': f'LLM error: {e}'}

    # ------------------------------------------------------------
    def command_cb(self, msg):
        user_text = msg.data
        self.get_logger().info(f'User: {user_text}')

        waypoints = self.load_waypoints()
        result = self.query_llm(user_text, waypoints)
        self.get_logger().info(f'LLM result: {result}')

        action = result.get('action', 'unknown')
        message = result.get('message', '')
        if message:
            self.get_logger().info(f'Robot: {message}')

        if action == 'navigate_to_pose':
            self.handle_navigate(
                result.get('waypoints', []), through=False,
                waypoints=waypoints)
        elif action == 'navigate_through_poses':
            self.handle_navigate(
                result.get('waypoints', []), through=True,
                waypoints=waypoints)
        elif action == 'save_waypoint':
            name = result.get('new_name', '').strip()
            if name:
                self.save_pub.publish(String(data=name))
        elif action == 'cancel':
            self.handle_cancel()
        else:
            pass  # 'unknown' - message already logged above

    # ------------------------------------------------------------
    def make_pose(self, w):
        pose = PoseStamped()
        pose.header.frame_id = self.map_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(w['x'])
        pose.pose.position.y = float(w['y'])
        qx, qy, qz, qw = yaw_to_quaternion(float(w.get('yaw', 0.0)))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def handle_navigate(self, names, through, waypoints):
        if not names:
            self.get_logger().warn('No waypoints given, nothing to do')
            return

        unknown = [n for n in names if n not in waypoints]
        if unknown:
            self.get_logger().warn(
                f'Unknown waypoint(s): {unknown}. '
                f'Known: {list(waypoints.keys())}')
            return

        poses = [self.make_pose(waypoints[n]) for n in names]

        if through and len(poses) > 1:
            goal = NavigateThroughPoses.Goal()
            goal.poses = poses
            client = self.nav_through_poses_client
        else:
            goal = NavigateToPose.Goal()
            goal.pose = poses[0]
            client = self.nav_to_pose_client

        self.get_logger().info(f'Sending navigation goal: {names}')
        client.wait_for_server()
        self._active_client = client
        send_future = client.send_goal_async(goal)
        send_future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected')
            self._goal_handle = None
            return
        self.get_logger().info('Goal accepted')
        self._goal_handle = goal_handle

    def handle_cancel(self):
        if self._goal_handle is not None:
            self.get_logger().info('Cancelling current goal')
            self._goal_handle.cancel_goal_async()
        else:
            self.get_logger().info('No active goal to cancel')


def main():
    rclpy.init()
    node = LLMCommander()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
