import threading
import queue
from typing import Callable
from .server_utils import _connection_manager_worker

class TialityServerManager:
    def __init__(
        self,
        mqtt_port: int,
        mqtt_broker_host_ip: str,
    ):
        """
        Headless server manager that can operate in:
          - Command-only mode
          - Video + command mode
        """
        print("server manager created")
        self.servers_active = False

        # Thread-safe queues
        # self.incoming_video_queue = queue.Queue(maxsize=1)
        # self.decoded_video_queue = queue.Queue(maxsize=1)
        self.command_queue = queue.Queue(maxsize=1)

        # Connection info
        self.mqtt_port = mqtt_port
        self.mqtt_broker_host_ip = mqtt_broker_host_ip
        self.tx_topic = "robot/tx"
        self.rx_topic = "robot/rx"

        # Thread and shutdown management
        self._connection_manager_thread = None
        self.shutdown_event = threading.Event()
        self.shutdown_event.clear()
        self.connection_established_event = threading.Event()

        # Track threads
        self._connection_threads = {
            "command_sender": None
        }

    def start_servers(self):
        """Start the connection manager in a separate thread (non-blocking)."""
        if self._connection_manager_thread is None or not self._connection_manager_thread.is_alive():
            self._connection_manager_thread = threading.Thread(
                target=_connection_manager_worker,
                args=(
                    self.mqtt_broker_host_ip,
                    self.mqtt_port,
                    self.tx_topic,
                    self.rx_topic,
                    self.command_queue,
                    self.connection_established_event,
                    self.shutdown_event,
                    self._connection_threads
                ),
                daemon=True
            )
            self._connection_manager_thread.start()
            self.servers_active = True

    def send_command(self, command):
        """Queue a command to be sent to the robot."""
        if self.servers_active:
            try:
                self.command_queue.get_nowait()  # discard old command
            except queue.Empty:
                pass
            try:
                self.command_queue.put_nowait(command)
            except queue.Full:
                pass

    def close_servers(self):
        """Signal shutdown and join connection manager thread."""
        self.shutdown_event.set()
        if self._connection_manager_thread and self._connection_manager_thread.is_alive():
            self._connection_manager_thread.join()
        self.servers_active = False
