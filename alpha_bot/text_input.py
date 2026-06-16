import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TextInput(Node):
    

    def __init__(self):
        super().__init__('text_input')
        self.pub = self.create_publisher(String, '/user_command', 10)
        self.get_logger().info(
            'Type a command and press Enter (Ctrl+C to quit).')

    def run(self):
        while rclpy.ok():
            try:
                text = input('> ')
            except EOFError:
                break
            text = text.strip()
            if not text:
                continue
            msg = String()
            msg.data = text
            self.pub.publish(msg)


def main():
    rclpy.init()
    node = TextInput()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
