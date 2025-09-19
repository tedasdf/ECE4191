import pygame
import sys
import logging
import cv2
import numpy as np
import os
import json
from typing import Callable, Optional, List
from gui_config import ConnectionStatus, ArmState, Colour, GuiConfig

# Get the parent directory path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Now you can import modules from the parent directory
from tiality_server import TialityServerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _decode_video_frame_opencv(frame_bytes: bytes) -> pygame.Surface:
    """
    Decodes a byte array (JPEG) into a Pygame surface using the highly
    optimized OpenCV library. This is the recommended, high-performance method.

    Args:
        frame_bytes: The raw byte string of a single JPEG image.

    Returns:
        A Pygame.Surface object, or None if decoding fails.
    """
    try:
        # 1. Convert the raw byte string to a 1D NumPy array.
        #    This is a very fast, low-level operation.
        np_array = np.frombuffer(frame_bytes, np.uint8)
        
        # 2. Decode the NumPy array into an OpenCV image.
        #    This is the core, high-speed decoding step. The result is in BGR format.
        img_bgr = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        img_bgr = cv2.resize(img_bgr, (510, 230), interpolation=cv2.INTER_AREA)

        # 3. Convert the color format from BGR (OpenCV's default) to RGB (Pygame's default).
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # 4. Correct the orientation. OpenCV arrays are (height, width), but
        #    pygame.surfarray.make_surface expects (width, height). We swap the axes.
        img_rgb = img_rgb.swapaxes(0, 1)

        # 5. Create a Pygame surface directly from the NumPy array.
        #    This is another very fast, low-level operation.
        frame_surface = pygame.surfarray.make_surface(img_rgb)
        
        return frame_surface
        
    except Exception as e:
        # If any part of the decoding fails (e.g., due to a corrupted frame),
        # print an error and return None so the GUI doesn't crash.
        print(f"Error decoding frame with OpenCV: {e}")
        return None



class ExplorerGUI:
    """
    INITIALISATION:
    Wildlife Explorer RC Car Controller GUI.
    
    Provides a graphical interface for controlling an RC car with dual camera feeds,
    movement controls, and arm manipulation capabilities.
    """

    def __init__(
        self, 
        background_image_path: str, 
        command_callback: Optional[Callable[[str], None]] = None,
        is_robot: bool = True,
        mqtt_broker_host_ip: str = "localhost",
        mqtt_port: int = 1883,
    ):
        """
        Args:
            background_image_path: Path to the background image file
            command_callback: Callback function for handling commands to PI
        """
        # Initialise core components
        pygame.init()
        self.config = GuiConfig()
        self.colours = Colour()
        self.is_robot = is_robot
        
        # Setup display and resources
        # self._load_background(background_image_path)
        # self._init_display()
        # self._init_fonts()
        # self._init_camera_layout()
        
        # Initialise application state
        self._init_state()
        
        # Initialise joystick (if present)
        try:
            pygame.joystick.init()
            self.joystick = None
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                if not self.joystick.get_init():
                    self.joystick.init()
                logger.info(f"Joystick initialised: {self.joystick.get_name()} | axes={self.joystick.get_numaxes()}")
            else:
                logger.info("No joystick detected")
        except Exception as e:
            self.joystick = None
            logger.warning(f"Joystick init failed: {e}")
        
        # Setup Server and shared frame queue
        self.server_manager = TialityServerManager(
            grpc_port = 50051,
            mqtt_port = mqtt_port, 
            mqtt_broker_host_ip = mqtt_broker_host_ip,
            decode_video_func = _decode_video_frame_opencv,
            num_decode_video_workers = 1 # Don't change this for now
            )
        self.server_manager.start_servers()

        # Setup timing
        self.clock = pygame.time.Clock()
        self.running = True
        
        logger.info("Wildlife Explorer GUI initialised successfully")

    # ============================================================================
    # INIT METHODS
    # ============================================================================

    def _init_fonts(self) -> None:
        self.fonts = {
            'small': pygame.font.Font(None, 20),
            'medium': pygame.font.Font(None, 28),
            'large': pygame.font.Font(None, 36)
        }

    def _init_camera_layout(self) -> None:
        # Camera feed positions (left and right)
        self.camera_positions = [
            (35, 255),   # Camera 1 position (left)
            (450, 170),  # Camera 2 position (right)
        ]
        
        self.camera_surfaces = [None] * self.config.NUM_CAMERAS
        self.camera_threads = []
        
        # Status indicator positions for each camera
        self.camera_indicator_positions = [
            (370, self.config.SCREEN_HEIGHT - 500),   # Camera 1 indicator
            (909, self.config.SCREEN_HEIGHT - 500)    # Camera 2 indicator
        ]

    def _init_state(self) -> None:
        """Initialise Explorer Control state variables."""
        # Movement control states
        # Set default keybindings
        if self.is_robot:
            # Robot default: no movement (stop command)
            self.default_keys = {"type": "all", "action": "stop"}
            # Keep movement_keys empty in robot mode; we send commands directly
            self.movement_keys = {}
        else:
            self.default_keys = {}
            self.default_keys["up"] = False
            self.default_keys["down"] = False
            self.default_keys["rotate_left"] = False
            self.default_keys["rotate_right"] = False
            self.default_keys["left"] = False
            self.default_keys["right"] = False
            self.movement_keys = self.default_keys.copy()
        
        # Camera states (all cameras start active)
        self.camera_states = [True] * self.config.NUM_CAMERAS
        
        # Hardware states
        self.arm_state = ArmState.RETRACTED
        self.connection_status = ConnectionStatus.DISCONNECTED

    # ============================================================================
    # COMMAND AND STATUS METHODS
    # ============================================================================

    def send_command(self, command: str) -> None:
        """
        Send command to Pi via callback function 
        """
        try:
            self.server_manager.send_command(command)
            logger.debug(f"Command sent: {command}")
        except Exception as e:
            logger.error(f"Command callback error: {e}")


    # ============================================================================
    # MOVEMENT HANDLING
    # ============================================================================

    def _get_active_movements(self) -> List[str]:
        """
        Get list of currently active movement directions.
        """
        # return [
        #     direction.upper() 
        #     for direction, is_active in self.movement_keys.items() 
        #     if is_active
        # ]
        
        return self.movement_keys

    def handle_movement(self) -> None:
        """Process current movement key states and send commands."""
        if self.is_robot:
            # Robot mode publishes movement in _handle_movement_keys; avoid duplicate sends
            return
        active_movements = self._get_active_movements()
        
        if active_movements:
            # Build movement command from active directions
            
            json_string = json.dumps(active_movements)
            encoded_string = json_string.encode()
            self.send_command(encoded_string)

    # ============================================================================
    # DRAWING METHODS
    # ============================================================================





    # ============================================================================
    # HELP SYSTEM
    # ============================================================================
    def _wait_for_keypress(self) -> None:
        waiting_for_input = True
        
        while waiting_for_input and self.running:
            for event in pygame.event.get():
                if event.type in (pygame.KEYDOWN, pygame.QUIT):
                    waiting_for_input = False
                    
                    if event.type == pygame.QUIT:
                        self.server_manager.close_servers()
                        self.running = False

    # ============================================================================
    # EVENT HANDLING
    # ============================================================================

    def _handle_movement_keys(self, event: pygame.event.Event, is_key_pressed: bool) -> None:
        """
        Handle movement key press/release events.
        
        Args:
            event: Pygame event object
            is_key_pressed: True for key press, False for key release
        """
        keys = self.default_keys.copy()

        # Get movement keys from pygame
        if self.is_robot:
            # Robot motion publishing is handled each frame in update()
            return
        else:
            pygame_keys = pygame.key.get_pressed()
            keys["up"] = pygame_keys[pygame.K_w] or pygame_keys[pygame.K_UP]
            keys["down"] = pygame_keys[pygame.K_s] or pygame_keys[pygame.K_DOWN]
            keys["rotate_left"] = pygame_keys[pygame.K_q]
            keys["rotate_right"] = pygame_keys[pygame.K_e]
            keys["left"] = pygame_keys[pygame.K_a]
            keys["right"] = pygame_keys[pygame.K_d]
        
        if not self.is_robot:
            self.movement_keys = keys.copy()

    def _publish_robot_motion(self) -> None:
        """Read joystick/keyboard state and publish a single motion command."""
        vx = 0.0
        vy = 0.0
        w = 0.0

        try:
            if self.joystick is not None and self.joystick.get_init():
                try:
                    x_axis = self.joystick.get_axis(0)
                except Exception:
                    x_axis = 0.0
                try:
                    y_axis = self.joystick.get_axis(1)
                except Exception:
                    y_axis = 0.0
                try:
                    rot_axis = self.joystick.get_axis(2)
                except Exception:
                    rot_axis = 0.0

                JOY_MAX_SPEED = 40.0
                JOY_MAX_ROT = 40.0
                vx = max(-100.0, min(100.0, x_axis * JOY_MAX_SPEED))
                vy = max(-100.0, min(100.0, -y_axis * JOY_MAX_SPEED))
                w = max(-100.0, min(100.0, rot_axis * JOY_MAX_ROT))
        except Exception:
            pass

        # Keyboard overrides/additions
        pygame_keys = pygame.key.get_pressed()
        key_speed = 50.0
        rot_speed = 40.0
        if pygame_keys[pygame.K_a]:
            vx = -key_speed
        if pygame_keys[pygame.K_d]:
            vx = key_speed
        if pygame_keys[pygame.K_w] or pygame_keys[pygame.K_UP]:
            vy = key_speed
        if pygame_keys[pygame.K_s] or pygame_keys[pygame.K_DOWN]:
            vy = -key_speed
        if pygame_keys[pygame.K_q]:
            w = -rot_speed
        if pygame_keys[pygame.K_e]:
            w = rot_speed

        # Deadzone to avoid noise
        DEADZONE = 0.10
        if abs(vx) < DEADZONE * 100.0:
            vx = 0.0
        if abs(vy) < DEADZONE * 100.0:
            vy = 0.0
        if abs(w) < DEADZONE * 100.0:
            w = 0.0

        # Emit command: vector if movement present, else stop
        if (vx != 0.0) or (vy != 0.0) or (w != 0.0):
            cmd = {"type": "vector", "action": "set", "vx": int(vx), "vy": int(vy), "w": int(w)}
        else:
            cmd = self.default_keys

        try:
            print(cmd)
            self.send_command(json.dumps(cmd).encode())
        except Exception as e:
            logger.error(f"Failed to send movement command: {e}")

    def _handle_function_keys(self, event: pygame.event.Event) -> None:
        key = event.key
        
        if key == pygame.K_SPACE:
            pass
            #self.send_command(json.dumps(self.default_keys.copy()).encode())
        elif key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_h:
            self.show_help()
        elif key in (pygame.K_1, pygame.K_2):
            self._handle_camera_toggle(key)
        elif key in (pygame.K_x, pygame.K_c):
            self._handle_arm_control(key)

    def _handle_camera_toggle(self, key: int) -> None:
        camera_index = 0 if key == pygame.K_1 else 1
        self.camera_states[camera_index] = not self.camera_states[camera_index]
        
        # Send appropriate command
        camera_number = camera_index + 1
        state = "ON" if self.camera_states[camera_index] else "OFF"
        command = f'CAMERA_{camera_number}_{state}'
        
        #self.send_command(command)

    def _handle_arm_control(self, key: int) -> None:
        if key == pygame.K_x:
            self.arm_state = ArmState.EXTENDED
            #self.send_command('ARM_EXTEND')
        elif key == pygame.K_c:
            self.arm_state = ArmState.RETRACTED
            #self.send_command('ARM_CONTRACT')

    def handle_events(self) -> None:
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_movement_keys(event, True)
                self._handle_function_keys(event)
            elif event.type == pygame.KEYUP:
                self._handle_movement_keys(event, False)

    # ============================================================================
    # MAIN LOOP METHODS
    # ============================================================================

    def update(self) -> None:
        """Update game state (called once per frame)."""
        if self.is_robot:
            self._publish_robot_motion()
        else:
            self.handle_movement()

    def run(self) -> None:
        """Main game loop with proper separation of concerns."""
        logger.info("Starting Wildlife Explorer GUI...")
        logger.info("Press 'H' for help, 'ESC' to exit")
        
        #TODO: Implement camera initialisation and streaming (Vinay)
        # self.start_camera_streams()
        
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.clock.tick(self.config.FPS)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources before exit."""
        logger.info("Cleaning up resources...")
        self.server_manager.close_servers()
        pygame.quit()
        sys.exit()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import os
    import argparse
    parser = argparse.ArgumentParser(description="Wildlife Explorer RC Car Controller")
    parser.add_argument("--robot", action='store_true', help="Whether to run the robot or sim")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host/IP for robot mode")
    parser.add_argument("--broker_port", type=int, default=1883, help="MQTT broker TCP port for robot mode")
    args = parser.parse_args()
    gui_type = "Robot" if args.robot else "Sim"
    print(f"Wildlife Explorer for {gui_type}")
    print("==================================")
    print("1280x720 HD Interface")
    print()
    
    # Configure Background Path
    image_path = "GUI/wildlife_explorer_cams_open.png"
    
    if not os.path.exists(image_path):
        print(f"Image file '{image_path}' not found.")
        print("Place your image in the same folder and update the path.")
        print("Using fallback background for now...")
    
    #TODO: Implement your command callback function
    def command_callback(command: str) -> None:
        logger.info(f"GUI Command: {command}")
    
    try:
        gui = ExplorerGUI(image_path, command_callback, args.robot, mqtt_broker_host_ip=args.broker, mqtt_port=args.broker_port)
        gui.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)