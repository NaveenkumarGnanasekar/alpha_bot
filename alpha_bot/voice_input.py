import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


SAMPLE_RATE = 16000


class VoiceInput(Node):


    def __init__(self):
        super().__init__('voice_input')

        if sd is None:
            self.get_logger().error(
                'sounddevice not installed. Run: pip install sounddevice')
            raise SystemExit(1)
        if WhisperModel is None:
            self.get_logger().error(
                'faster-whisper not installed. '
                'Run: pip install faster-whisper')
            raise SystemExit(1)

        self.declare_parameter('model_size', 'base.en')
        model_size = self.get_parameter(
            'model_size').get_parameter_value().string_value

        self.pub = self.create_publisher(String, '/user_command', 10)

        self.get_logger().info(
            f'Loading whisper model "{model_size}" '
            '(first run downloads it)...')
        self.model = WhisperModel(model_size, device='cpu', compute_type='int8')
        self.get_logger().info(
            'Voice input ready. Press Enter, speak, press Enter again '
            'to stop.')

    def record_until_enter(self):
        frames = []

        def callback(indata, frames_count, time_info, status):
            frames.append(indata.copy())

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype='float32',
            callback=callback)
        with stream:
            input()  # block until user presses Enter again

        if not frames:
            return np.array([], dtype='float32')
        return np.concatenate(frames, axis=0).flatten()

    def run(self):
        while rclpy.ok():
            input('\nPress Enter to start recording...')
            print('Recording... press Enter to stop.')
            audio = self.record_until_enter()
            if audio.size == 0:
                continue

            print('Transcribing...')
            segments, _ = self.model.transcribe(audio, language='en')
            text = ' '.join(seg.text for seg in segments).strip()
            if not text:
                print('(heard nothing)')
                continue

            print(f'Heard: {text}')
            msg = String()
            msg.data = text
            self.pub.publish(msg)


def main():
    rclpy.init()
    node = VoiceInput()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
