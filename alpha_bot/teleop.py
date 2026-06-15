#!/usr/bin/env python3
"""
Keyboard teleop node for alpha_bot (differential drive).

Publishes to /cmd_vel (geometry_msgs/Twist).
Bridge this to Gazebo with ros_gz_bridge.

Controls:
  w / s  : forward / backward
  a / d  : turn left / right
  q / e  : strafe-turn (arc left / arc right)
  space  : stop
  +/-    : increase/decrease speed
  Ctrl+C : quit
"""

import sys
import tty
import termios
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

BANNER = """
╔══════════════════════════════════════╗
║      alpha_bot keyboard teleop       ║
╠══════════════════════════════════════╣
║  w/s    : forward / backward         ║
║  a/d    : turn left / right          ║
║  q/e    : arc left / arc right       ║
║  space  : STOP                       ║
║  +/-    : speed up / slow down       ║
║  Ctrl+C : quit                       ║
╚══════════════════════════════════════╝
"""

# Differential drive parameters (from URDF)
WHEEL_RADIUS    = 0.205   # metres
WHEEL_SEPARATION = 0.5339  # metres (left Y - right Y)

# Default speeds
LINEAR_STEP  = 0.05   # m/s per keypress
ANGULAR_STEP = 0.1    # rad/s per keypress
MAX_LINEAR   = 0.5    # m/s
MAX_ANGULAR  = 1.5    # rad/s

KEY_BINDINGS = {
    'w': ( 1,  0),   # forward
    's': (-1,  0),   # backward
    'a': ( 0,  1),   # turn left
    'd': ( 0, -1),   # turn right
    'q': ( 1,  1),   # arc left
    'e': ( 1, -1),   # arc right
    ' ': ( 0,  0),   # stop (absolute zero)
}

SPEED_KEYS = {'+', '=', '-', '_'}


def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('alpha_bot_teleop')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.linear  = 0.0
        self.angular = 0.0
        self.speed_scale = 1.0
        self.get_logger().info('Teleop node ready — focus this terminal and use keys')

    def publish(self, linear, angular):
        msg = Twist()
        msg.linear.x  = float(linear)
        msg.angular.z = float(angular)
        self.pub.publish(msg)

    def run(self):
        settings = termios.tcgetattr(sys.stdin)
        print(BANNER)
        print(f"Speed scale: {self.speed_scale:.1f}x  (linear={self.linear:.2f} m/s  angular={self.angular:.2f} rad/s)")
        try:
            while rclpy.ok():
                key = get_key(settings)

                if key == '\x03':   # Ctrl+C
                    break

                if key in SPEED_KEYS:
                    if key in ('+', '='):
                        self.speed_scale = min(2.0, self.speed_scale + 0.1)
                    else:
                        self.speed_scale = max(0.1, self.speed_scale - 0.1)
                    print(f"\rSpeed scale: {self.speed_scale:.1f}x", end='', flush=True)
                    continue

                if key == ' ':
                    self.linear  = 0.0
                    self.angular = 0.0
                    self.publish(0.0, 0.0)
                    print(f"\r[STOP]  linear=0.00 m/s  angular=0.00 rad/s    ", end='', flush=True)
                    continue

                if key in KEY_BINDINGS:
                    dl, da = KEY_BINDINGS[key]
                    self.linear  += dl * LINEAR_STEP  * self.speed_scale
                    self.angular += da * ANGULAR_STEP * self.speed_scale

                    # Clamp
                    self.linear  = max(-MAX_LINEAR,  min(MAX_LINEAR,  self.linear))
                    self.angular = max(-MAX_ANGULAR, min(MAX_ANGULAR, self.angular))

                    self.publish(self.linear, self.angular)
                    print(
                        f"\r[{key}]  linear={self.linear:+.2f} m/s  "
                        f"angular={self.angular:+.2f} rad/s    ",
                        end='', flush=True
                    )

        finally:
            # Always send stop on exit
            self.publish(0.0, 0.0)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            print('\nStopped.')


def main():
    rclpy.init()
    node = TeleopKeyboard()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
