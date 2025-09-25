import threading
from .video_streaming import server as video_server
from .video_streaming import decoder_worker
from .command_streaming import publisher as command_publisher


def _connection_manager_worker(
    grpc_port,
    incoming_video_queue,
    decoded_video_queue,
    mqtt_broker_host_ip,
    mqtt_port,
    tx_topic,
    rx_topic,
    command_queue,
    connection_established_event,
    shutdown_event,
    decode_video_func=None,
    num_decode_video_workers=0,
):
    """
    Thread to manage connections.
    If decode_video_func and num_decode_video_workers > 0 are provided,
    video producer + decoder threads will be started.
    Otherwise, runs in command-only mode.
    """

    video_enabled = decode_video_func is not None and num_decode_video_workers > 0

    video_producer_thread = None
    video_decoder_threads = (
        [None for _ in range(num_decode_video_workers)] if video_enabled else []
    )
    command_sender_thread = None

    try:
        while not shutdown_event.is_set():
            try:
                # --- VIDEO (optional) ---
                if video_enabled:
                    if video_producer_thread is None or not video_producer_thread.is_alive():
                        print("Waiting for Video Connection")
                        video_producer_thread = threading.Thread(
                            target=video_server.serve,
                            args=(grpc_port, incoming_video_queue, connection_established_event, shutdown_event),
                        )
                        video_producer_thread.start()

                    for i in range(num_decode_video_workers):
                        if video_decoder_threads[i] is None or not video_decoder_threads[i].is_alive():
                            video_decoder_threads[i] = threading.Thread(
                                target=decoder_worker.start_decoder_worker,
                                args=(incoming_video_queue, decoded_video_queue, decode_video_func, shutdown_event),
                            )
                            video_decoder_threads[i].start()

                # --- COMMAND ---
                if command_sender_thread is None or not command_sender_thread.is_alive():
                    print("Waiting for Command Sending Connection")
                    command_sender_thread = threading.Thread(
                        target=command_publisher.publish_commands_worker,
                        args=(mqtt_port, mqtt_broker_host_ip, command_queue, tx_topic, shutdown_event),
                    )
                    command_sender_thread.start()
                    connection_established_event.set()

            except Exception as e:
                print(f"Exception Encountered: {e}")
    finally:
        print("Ensuring Threads successfully shutdown")

        # Close video threads if used
        if video_producer_thread and video_producer_thread.is_alive():
            video_producer_thread.join()

        for video_decoder_thread in video_decoder_threads:
            if video_decoder_thread and video_decoder_thread.is_alive():
                video_decoder_thread.join()

        # Close command thread
        if command_sender_thread and command_sender_thread.is_alive():
            command_sender_thread.join()

        print("Connections shut down")
