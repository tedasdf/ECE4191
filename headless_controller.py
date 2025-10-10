import threading
import json
import logging
from inputs import get_gamepad

logger = logging.getLogger(__name__)

class HeadlessController:
    def __init__(self, mqtt_broker_host_ip="localhost", mqtt_port=1883):
        # Optional: replace this with your real server manager
        from tiality_server import TialityServerManager
        self.server_manager = TialityServerManager(
            grpc_port=50051,
            mqtt_port=mqtt_port,
            mqtt_broker_host_ip=mqtt_broker_host_ip,
            decode_video_func=None,
            num_decode_video_workers=0
        )
        self.server_manager.start_servers()

        self.axis_state = {
            "ABS_X": 0.0,   # Left stick X
            "ABS_Y": 0.0,   # Left stick Y
            "ABS_RX": 0.0,  # Right stick X
            "ABS_RY": 0.0,  # Right stick Y
        }
        self.button_state = {}
        self.running = True

        # start gamepad thread
        self.poll_thread = threading.Thread(target=self._poll_gamepad, daemon=True)
        self.poll_thread.start()

        # start command loop thread
    def start_loop(self):
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()

        print("🎮 Headless Windows controller started")

    def _poll_gamepad(self):
        """Continuously read inputs and update axis/button states."""
        while self.running:
            try:
                events = get_gamepad()
                for event in events:
                    if event.code in self.axis_state:
                        self.axis_state[event.code] = event.state / 32768.0
                    elif event.code.startswith("BTN_"):
                        self.button_state[event.code] = bool(event.state)
            except Exception:
                pass  # Ignore temporary disconnections

    def _command_loop(self, hz=30):
        """Send motion commands periodically."""
        import time
        period = 1.0 / hz
        while self.running:
            self._publish_robot_motion()
            time.sleep(period)

    def send_command(self, command: str):
        """Send command to MQTT or server."""
        try:
            self.server_manager.send_command(command)
        except Exception as e:
            logger.error(f"Command send failed: {e}")

    def _publish_robot_motion(self):
        """Compute robot velocity vector from joystick."""
        x_axis = self.axis_state.get("ABS_X", 0.0)
        y_axis = self.axis_state.get("ABS_Y", 0.0)
        rot_axis = self.axis_state.get("ABS_RX", 0.0)

        # Debug print
        # print(f"[AXIS] x={x_axis:.3f}, y={y_axis:.3f}, rot={rot_axis:.3f}")

        # Convert to velocity values
        vx = x_axis * 40.0
        vy = -y_axis * 40.0
        w = rot_axis * 40.0

        # Deadzone
        if abs(vx) < 5: vx = 0.0
        if abs(vy) < 5: vy = 0.0
        if abs(w) < 5: w = 0.0

        # Emit command
        if vx or vy or w:
            cmd = {"type": "vector", "action": "set", "vx": int(vx), "vy": int(vy), "w": int(w)}
            print(cmd)
        else:
            cmd = {"type": "all", "action": "stop"}
            print(cmd)

        self.send_command(json.dumps(cmd).encode())

    def send_gimbal_command(self, action: str, degrees: float = 10.0):
        """Send gimbal control command."""
        cmd = {
            "type": "gimbal",
            "action": action,
            "degrees": degrees
        }
        try:
            command_json = json.dumps(cmd).encode()
            self.send_command(command_json)
        except Exception as e:
            logger.error(f"Failed to send gimbal command: {e}")

    def stop(self):
        """Stop all threads cleanly."""
        self.running = False
        self.poll_thread.join(timeout=1)
        self.command_thread.join(timeout=1)
        self.server_manager.close_servers()
        print("🛑 Controller stopped cleanly")