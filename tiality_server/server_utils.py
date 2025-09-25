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
    threads_dict=None
):
    """
    Non-blocking connection manager for video + command threads.
    threads_dict: dictionary to track live threads
    """
    video_enabled = decode_video_func is not None and num_decode_video_workers > 0

    def try_start_threads():
        if shutdown_event.is_set():
            return  # stop retrying

        try:
            # --- Video ---
            if video_enabled:
                if threads_dict["video_producer"] is None or not threads_dict["video_producer"].is_alive():
                    threads_dict["video_producer"] = threading.Thread(
                        target=video_server.serve,
                        args=(grpc_port, incoming_video_queue, connection_established_event, shutdown_event),
                        daemon=True
                    )
                    threads_dict["video_producer"].start()

                for i in range(num_decode_video_workers):
                    if threads_dict["video_decoders"][i] is None or not threads_dict["video_decoders"][i].is_alive():
                        threads_dict["video_decoders"][i] = threading.Thread(
                            target=decoder_worker.start_decoder_worker,
                            args=(incoming_video_queue, decoded_video_queue, decode_video_func, shutdown_event),
                            daemon=True
                        )
                        threads_dict["video_decoders"][i].start()

            # --- Command ---
            if threads_dict["command_sender"] is None or not threads_dict["command_sender"].is_alive():
                threads_dict["command_sender"] = threading.Thread(
                    target=command_publisher.publish_commands_worker,
                    args=(mqtt_port, mqtt_broker_host_ip, command_queue, tx_topic, shutdown_event),
                    daemon=True
                )
                threads_dict["command_sender"].start()
                connection_established_event.set()

        except Exception as e:
            print(f"Exception in connection manager: {e}")

        # Retry after 2 seconds if not shutdown
        if not shutdown_event.is_set():
            threading.Timer(2.0, try_start_threads).start()

    # Initial attempt
    try_start_threads()

    # Wait until shutdown
    shutdown_event.wait()

    # Clean up threads
    for t in threads_dict.get("video_decoders", []) + [threads_dict.get("video_producer"), threads_dict.get("command_sender")]:
        if t and t.is_alive():
            t.join()
