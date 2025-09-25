import threading
import queue
from typing import Callable
from .server_utils import _connection_manager_worker

class TialityServerManager:
    def __init__(
        self,
        grpc_port: int,
        mqtt_port: int,
        mqtt_broker_host_ip: str,
        decode_video_func: Callable = None,
        num_decode_video_workers: int = 0
    ):
        """
        Headless server manager that can operate in:
          - Command-only mode
          - Video + command mode
        """
        self.servers_active = False
        self.decode_video_func = decode_video_func
        self.num_decode_video_workers = num_decode_video_workers

        # Thread-safe queues
        self.incoming_video_queue = queue.Queue(maxsize=1)
        self.decoded_video_queue = queue.Queue(maxsize=1)
        self.command_queue = queue.Queue(maxsize=1)

        # Connection info
        self.grpc_port = grpc_port
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
            "video_producer": None,
            "video_decoders": [None] * num_decode_video_workers if decode_video_func else [],
            "command_sender": None
        }

    def start_servers(self):
        """Start the connection manager in a separate thread (non-blocking)."""
        if self._connection_manager_thread is None or not self._connection_manager_thread.is_alive():
            self._connection_manager_thread = threading.Thread(
                target=_connection_manager_worker,
                args=(
                    self.grpc_port,
                    self.incoming_video_queue,
                    self.decoded_video_queue,
                    self.mqtt_broker_host_ip,
                    self.mqtt_port,
                    self.tx_topic,
                    self.rx_topic,
                    self.command_queue,
                    self.connection_established_event,
                    self.shutdown_event,
                    self.decode_video_func,
                    self.num_decode_video_workers,
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

    def get_video_frame(self):
        """Return the latest decoded video frame if available."""
        if self.servers_active and self.decode_video_func:
            try:
                return self.decoded_video_queue.get_nowait()
            except queue.Empty:
                return None
        return None

    def close_servers(self):
        """Signal shutdown and join connection manager thread."""
        self.shutdown_event.set()
        if self._connection_manager_thread and self._connection_manager_thread.is_alive():
            self._connection_manager_thread.join()
        self.servers_active = False
