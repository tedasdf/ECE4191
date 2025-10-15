import threading
import json
import logging
import time
from inputs import get_gamepad

logger = logging.getLogger(__name__)

class HeadlessController:
    def __init__(self, mqtt_broker_host_ip="localhost", mqtt_port=1883):
        # Optional: replace this with your real server manager
        from tiality_server import TialityServerManager
        self.server_manager = TialityServerManager(
            mqtt_port=mqtt_port,
            mqtt_broker_host_ip=mqtt_broker_host_ip
        )
        self.server_manager.start_servers()

        self.axis_state = {
            "ABS_X": 0.0,   # Left stick X
            "ABS_Y": 0.0,   # Left stick Y
            "ABS_RX": 0.0,  # Right stick X
            "ABS_RY": 0.0,  # Right stick Y
        }
        self.button_state = {}

    def start_loop(self, poll_hz=30, cmd_hz=30):
        self.running = True
        # Timer handles for cancellation
        self._poll_timer = None
        self._cmd_timer = None
        # Non-reentrancy guard for command publisher
        self._cmd_lock = getattr(self, "_cmd_lock", threading.Lock())

        # Kick off self-rescheduling tasks (no dedicated threads needed)
        self._poll_gamepad(hz=poll_hz)
        self._command_loop(hz=cmd_hz)

    print("🎮 Headless Windows controller began")

    def _poll_gamepad(self, hz=30):
        """Poll once, update states, and reschedule without blocking."""
        if not getattr(self, "running", False):
            return

        try:
            events = get_gamepad()  # If this blocks, it only blocks this tick.
            for event in events:
                if event.code in self.axis_state:
                    self.axis_state[event.code] = event.state / 32768.0
                elif event.code.startswith("BTN_"):
                    self.button_state[event.code] = bool(event.state)
        except Exception:
            pass  # Ignore temporary disconnections

        # Schedule next tick
        delay = max(0.0, 1.0 / float(hz))
        t = threading.Timer(delay, self._poll_gamepad, kwargs={"hz": hz})
        t.daemon = True
        self._poll_timer = t
        t.start()

    def _command_loop(self, hz=30):
        """Send motion commands periodically without blocking the caller."""
        if not getattr(self, "running", False):
            return

        # Try a non-blocking acquire — if the previous tick is still running, skip this one.
        acquired = self._cmd_lock.acquire(blocking=False)
        if acquired:
            try:
                self._publish_robot_motion()
            finally:
                self._cmd_lock.release()

        # Schedule next tick
        delay = max(0.0, 1.0 / float(hz))
        t = threading.Timer(delay, self._command_loop, kwargs={"hz": hz})
        t.daemon = True
        self._cmd_timer = t
        t.start()

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

    def stop_loop(self):
        """Stop everything and cancel scheduled timers."""
        self.running = False
        t = getattr(self, "_poll_timer", None)
        if t is not None:
            t.cancel()
            self._poll_timer = None
        t = getattr(self, "_cmd_timer", None)
        if t is not None:
            t.cancel()
            self._cmd_timer = None