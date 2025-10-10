import pygame
import logging
import json
from tiality_server import TialityServerManager
import threading
import os

logger = logging.getLogger(__name__)

class HeadlessController:
    def __init__(self, mqtt_broker_host_ip="localhost", mqtt_port=1883):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.joystick.init()
        print("Controller started")
        pygame.display.set_mode((1, 1))

        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Joystick initialised: {self.joystick.get_name()}")
            # print(self.joystick) #testing command

        # self.pygame_keys = None
        # pygame.key.get_pressed()
        

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
        # print(command) #testing command
        try:
            self.server_manager.send_command(command)
        except Exception as e:
            logger.error(f"Command send failed: {e}")

    def _publish_robot_motion(self):
        vx = vy = w = 0.0

        # Joystick input
        if self.joystick and self.joystick.get_init():
            try:
                pygame.event.pump()
                x_axis = self.joystick.get_axis(0)
                y_axis = self.joystick.get_axis(1)
                rot_axis = self.joystick.get_axis(2)
                print(x_axis, y_axis, rot_axis) # testing command

            except Exception:
                x_axis = y_axis = rot_axis = 0.0

            vx = x_axis * 40.0
            vy = -y_axis * 40.0
            w = rot_axis * 40.0

        # x_axis = y_axis = rot_axis = 0.0
        # print(x_axis, y_axis, rot_axis) # testing command

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

    def send_gimbal_command(self, action: str, degrees: float = 10.0) -> None:
        """
        Send gimbal command to Pi via MQTT - immediate response
        
        Args:
            action: The gimbal action (x_left, x_right, y_up, y_down, c_up, c_down, center)
            degrees: How many degrees to move (default 10.0)
        """
        # print("send gimbal command called")
        cmd = {
            "type": "gimbal",
            "action": action,
            "degrees": degrees
        }
        
        try:
            command_json = json.dumps(cmd).encode()
            logger.info(f"Sending gimbal command: {cmd}")
            self.send_command(command_json)
            logger.info(f"Gimbal command queued successfully: {cmd}")
        except Exception as e:
            logger.error(f"Failed to send gimbal command: {e}")
            raise


    def update(self, hz):
        """Call this once per frame from tkinter loop."""
        # for event in pygame.event.get():
        #     if event.type == pygame.QUIT:
        #         self.running = False

        if self.running:
            self._publish_robot_motion()
            self.clock.tick(hz)  # 30Hz
            for event in pygame.event.get():
                print(f"event: {event}")

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

