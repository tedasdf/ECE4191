import threading
import queue
from .server_utils import _connection_manager_worker


class TialityServerManager:
    def __init__(
        self,
        grpc_port: int,
        mqtt_port: int,
        mqtt_broker_host_ip: str,
        decode_video_func=None,
        num_decode_video_workers: int = 0,
    ):
        """
        Tiality Robot Server Manager

        Args:
            grpc_port (int): gRPC port (used if video is enabled)
            mqtt_port (int): MQTT broker port
            mqtt_broker_host_ip (str): MQTT broker host
            decode_video_func (Callable | None): function to decode video frames, or None for command-only
            num_decode_video_workers (int): number of decoder threads (0 = disable video)

        Command only:
        manager = TialityServerManager(
            grpc_port=50051,
            mqtt_port=1883,
            mqtt_broker_host_ip="localhost",
            decode_video_func=None,
            num_decode_video_workers=0,
        )

        Video + Command:
        manager = TialityServerManager(
            grpc_port=50051,
            mqtt_port=1883,
            mqtt_broker_host_ip="localhost",
            decode_video_func=my_decoder_func,
            num_decode_video_workers=1,
        )
        """
        self.servers_active = False

        self.decode_video_func = decode_video_func
        self.num_decode_video_workers = num_decode_video_workers

        # Queues
        self.incoming_video_queue = queue.Queue(maxsize=1) if self.video_enabled else None
        self.decoded_video_queue = queue.Queue(maxsize=1) if self.video_enabled else None
        self.command_queue = queue.Queue(maxsize=1)

        self.grpc_port = grpc_port
        self.mqtt_port = mqtt_port
        self.mqtt_broker_host_ip = mqtt_broker_host_ip
        self.tx_topic = "robot/tx"
        self.rx_topic = "robot/rx"

        self._connection_manager_thread = None
        self.shutdown_event = threading.Event()
        self.connection_established_event = threading.Event()

    @property
    def video_enabled(self):
        return self.decode_video_func is not None and self.num_decode_video_workers > 0

    def get_video_frame(self):
        if self.servers_active and self.video_enabled:
            try:
                return self.decoded_video_queue.get_nowait()
            except queue.Empty:
                return None
        return None

    def send_command(self, command):
        if self.servers_active:
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.command_queue.put_nowait(command)
            except queue.Full:
                pass

    def start_servers(self):
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
            ),
            daemon=True,
        )
        self._connection_manager_thread.start()
        self.servers_active = True

    def close_servers(self):
        if self.servers_active:
            self.shutdown_event.set()
            self._connection_manager_thread.join()
            self.servers_active = False
