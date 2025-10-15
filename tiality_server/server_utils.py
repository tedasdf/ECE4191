import threading
from .command_streaming import publisher as command_publisher

def _connection_manager_worker(
    mqtt_broker_host_ip,
    mqtt_port,
    tx_topic,
    rx_topic,
    command_queue,
    connection_established_event,
    shutdown_event,
    threads_dict=None
):
    """
    Non-blocking connection manager for video + command threads.
    threads_dict: dictionary to track live threads
    """

    print("attempting to connect")

    def try_start_threads():
        if shutdown_event.is_set():
            return  # stop retrying

        try:
            # --- Video ---

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
