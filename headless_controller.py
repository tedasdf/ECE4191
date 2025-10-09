import pygame
import logging
import json
import threading
import os
import sys
import platform
from tiality_server import TialityServerManager

# from tiality_server import TialityServerManager  # uncomment for real use
logger = logging.getLogger(__name__)


class DummyServerManager:
    """Stub for local testing without Tiality."""
    def __init__(self, *a, **kw): print("⚙️ DummyServerManager active")
    def start_servers(self): print("🟢 Servers started")
    def send_command(self, cmd): print("📤 Command:", cmd)
    def close_servers(self): print("🔴 Servers closed")


class HeadlessController:
    def __init__(self, mqtt_broker_host_ip="localhost", mqtt_port=1883):
        """Initialize joystick and comms."""
        system = platform.system()

        # --- ✅ Cross-platform SDL setup ---
        if system == "Windows":
            # Windows needs a real (but hidden) window for joystick input
            os.environ.pop("SDL_VIDEODRIVER", None)
            pygame.init()
            pygame.display.init()
            pygame.display.set_mode((1, 1))
            import ctypes
            hwnd = pygame.display.get_wm_info()["window"]
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # hide window
            print("🎮 Windows mode: hidden SDL window created")
        else:
            # Linux / Pi can run truly headless
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.init()
            pygame.display.init()
            pygame.display.set_mode((1, 1))
            print("🐧 Linux/Pi mode: dummy SDL driver active")

        pygame.joystick.init()
        self.clock = pygame.time.Clock()
        self.running = True

        # --- Joystick detection ---
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"✅ Joystick initialized: {self.joystick.get_name()}")
        else:
            print("⚠️ No joystick detected!")
            self.joystick = None

        # --- Replace with real server manager if available ---
        try:
            self.server_manager = TialityServerManager(
                grpc_port=50051,
                mqtt_port=mqtt_port,
                mqtt_broker_host_ip=mqtt_broker_host_ip,
                decode_video_func=None,
                num_decode_video_workers=0
            )
        except NameError:
            # fallback for local testing
            self.server_manager = DummyServerManager()

        self.server_manager.start_servers()

    # ------------------------------------------------------------------
    def send_command(self, command: str):
        try:
            self.server_manager.send_command(command)
        except Exception as e:
            logger.error(f"Command send failed: {e}")

    # ------------------------------------------------------------------
    def _publish_robot_motion(self):
        # print("function accessed")
        vx = vy = w = 0.0

        if self.joystick and self.joystick.get_init():
            try:
                pygame.event.pump()
                x_axis = self.joystick.get_axis(0)
                y_axis = self.joystick.get_axis(1)
                rot_axis = self.joystick.get_axis(2)
                print(f"[AXIS] {x_axis:.3f}, {y_axis:.3f}, {rot_axis:.3f}")
            except Exception:
                x_axis = y_axis = rot_axis = 0.0

            vx = x_axis * 40.0
            vy = -y_axis * 40.0
            w = rot_axis * 40.0

        # Deadzone
        if abs(vx) < 5: vx = 0.0
        if abs(vy) < 5: vy = 0.0
        if abs(w) < 5: w = 0.0

        if vx or vy or w:
            cmd = {"type": "vector", "action": "set", "vx": int(vx), "vy": int(vy), "w": int(w)}
        else:
            cmd = {"type": "all", "action": "stop"}
        self.send_command(json.dumps(cmd).encode())

    # ------------------------------------------------------------------
    def update(self, hz):
        """Run once per frame."""
        if not self.running:
            return
        self._publish_robot_motion()
        for event in pygame.event.get():
            print(f"[EVENT] {event}")
        self.clock.tick(hz)

    # ------------------------------------------------------------------
    def cleanup(self):
        self.server_manager.close_servers()
        pygame.quit()
        print("👋 Controller shut down cleanly")

    # ------------------------------------------------------------------
    def start_loop(self, hz):
        """Run in background thread at ~hz."""
        self.running = True

        def loop():
            while self.running:
                self.update(hz)
                self.clock.tick(hz)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        self._thread = t

    def stop_loop(self):
        self.running = False
        if hasattr(self, "_thread"):
            self._thread.join(timeout=1)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hc = HeadlessController()
    hc.start_loop(30)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        hc.stop_loop()
        hc.cleanup()
