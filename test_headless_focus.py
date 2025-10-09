import os
import time
import json
import logging
import pygame
import threading

# ---------------------------------------------------------------------
# ✅ MOCK server manager so we can run this standalone
# ---------------------------------------------------------------------
class DummyServerManager:
    def __init__(self, *args, **kwargs):
        print("⚙️ DummyServerManager initialized")

    def start_servers(self):
        print("🟢 Dummy servers started")

    def send_command(self, cmd):
        print("📤 Command sent:", cmd)

    def close_servers(self):
        print("🔴 Dummy servers closed")


# ---------------------------------------------------------------------
# ✅ Your HeadlessController (lightly simplified for testing)
# ---------------------------------------------------------------------
class HeadlessController:
    def __init__(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        pygame.joystick.init()
        time.sleep(0.1)

        self.clock = pygame.time.Clock()
        self.running = True

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"✅ Joystick initialized: {self.joystick.get_name()}")
        else:
            print("⚠️ No joystick detected!")
            self.joystick = None

        self.server_manager = DummyServerManager()
        self.server_manager.start_servers()

    def _publish_robot_motion(self):
        if not self.joystick or not self.joystick.get_init():
            return

        pygame.event.pump()

        x_axis = self.joystick.get_axis(0)
        y_axis = self.joystick.get_axis(1)
        rot_axis = self.joystick.get_axis(2)
        print(f"[AXIS] x={x_axis:.3f}, y={y_axis:.3f}, rot={rot_axis:.3f}")

    def update(self, hz=30):
        # Print any pygame events to check focus/queue
        events = pygame.event.get()
        if events:
            for event in events:
                print(f"[EVENT] {event}")

        self._publish_robot_motion()
        self.clock.tick(hz)

    def run(self, hz=30):
        print("🎮 Starting joystick focus test loop...")
        try:
            while self.running:
                self.update(hz)
        except KeyboardInterrupt:
            self.cleanup()

    def cleanup(self):
        self.server_manager.close_servers()
        pygame.quit()
        print("👋 Clean exit.")


# ---------------------------------------------------------------------
# ✅ Entry point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hc = HeadlessController()
    hc.run(20)
