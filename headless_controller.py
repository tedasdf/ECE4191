import pygame
import logging
import json
from tiality_server import TialityServerManager
import threading

logger = logging.getLogger(__name__)

class HeadlessController:
    def __init__(self, mqtt_broker_host_ip="localhost", mqtt_port=1883):
        pygame.init()
        pygame.joystick.init()

        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            logger.info(f"Joystick initialised: {self.joystick.get_name()}")

        self.server_manager = TialityServerManager(
            grpc_port=50051,
            mqtt_port=mqtt_port,
            mqtt_broker_host_ip=mqtt_broker_host_ip,
            decode_video_func=None,
            num_decode_video_workers=0
        )
        self.server_manager.start_servers()

        self.running = True

        self.clock = pygame.time.Clock()

    def send_command(self, command: str):
        try:
            self.server_manager.send_command(command)
        except Exception as e:
            logger.error(f"Command send failed: {e}")

    def _publish_robot_motion(self):
        vx = vy = w = 0.0

        # Joystick input
        if self.joystick and self.joystick.get_init():
            try:
                x_axis = self.joystick.get_axis(0)
                y_axis = self.joystick.get_axis(1)
                rot_axis = self.joystick.get_axis(2)
            except Exception:
                x_axis = y_axis = rot_axis = 0.0

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
        else:
            cmd = {"type": "all", "action": "stop"}

        self.send_command(json.dumps(cmd).encode())

    def update(self, hz):
        """Call this once per frame from tkinter loop."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        if self.running:
            self._publish_robot_motion()
            self.clock.tick(hz)  # 30Hz

    def cleanup(self):
        self.server_manager.close_servers()
        pygame.quit()

    def start_loop(self, hz):
        """Run update loop in a background thread at ~hz frequency."""
        self.running = True

        def loop():
            while self.running:
                self.update(hz)
                # keep frequency stable
                self.clock.tick(hz)


        t = threading.Thread(target=loop, daemon=True)
        t.start()
        self._thread = t

    def stop_loop(self):
        """Stop the background loop."""
        self.running = False
        if hasattr(self, "_thread"):
            self._thread.join(timeout=1)
