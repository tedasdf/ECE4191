import logging
import sys
import argparse
from typing import Optional

import cv2
import grpc
import numpy as np
import paho.mqtt.client as mqtt
import pygame
import queue

def connect_mqtt_async(mqtt_port: int, broker_host_ip: str) -> tuple[mqtt.Client, "threading.Event"]:
    """
    Initialise an MQTT client in async mode. Returns (client, connected_event).
    Paho handles network I/O on its own thread via loop_start().
    """
    connected_evt = None
    try:
        import threading
        connected_evt = threading.Event()
    except Exception:
        pass

    client = mqtt.Client()

    def _on_connect(cli, _userdata, _flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT broker at %s:%s", broker_host_ip, mqtt_port)
            if connected_evt:
                connected_evt.set()
        else:
            logging.error("Failed to connect to MQTT broker (rc=%s)", rc)

    def _on_disconnect(cli, _userdata, rc):
        logging.warning("Disconnected from MQTT (rc=%s)", rc)
        # allow reconnects; connected_evt will be cleared so we buffer again
        if connected_evt:
            try:
                connected_evt.clear()
            except Exception:
                pass

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect

    # Non-blocking connect; returns immediately
    client.connect_async(broker_host_ip, mqtt_port, keepalive=60)
    client.loop_start()
    return client, connected_evt

# def publish_commands_worker(mqtt_port: int, broker_host_ip: str, command_queue: queue.Queue, tx_topic: str, shutdown_event):

#     def publish_command(command: str, mqtt_client: mqtt.Client, tx_topic: str):
#         """Publish command via MQTT."""
#         try:
#             mqtt_client.publish(tx_topic, payload=command, qos=0)
#         except Exception as exc:
#             print(f"Failed to publish MQTT message: {exc}", exc)
    
#     mqtt_client = connect_mqtt_async(mqtt_port, broker_host_ip)
#     topic = tx_topic
    
#     try:
#         while not shutdown_event.is_set():
#             try:            
#                 # Attempt to retrieve new command
#                 command = command_queue.get_nowait()

#                 # Send command when available
#                 publish_command(command, mqtt_client, topic)

#             except queue.Empty:
#                 # No command in queue
#                 continue

#     finally:
#         mqtt_client.loop_stop()
#         mqtt_client.disconnect()
#         print("Commands Worker Thread shutting down")


def publish_commands_worker(
    mqtt_port: int,
    broker_host_ip: str,
    command_queue: queue.Queue,
    tx_topic: str,
    shutdown_event,  # threading.Event
    max_batch: int = 50,
    idle_wait_s: float = 0.05,
):
    """
    Non-blocking worker:
      - Never blocks the main/UI thread (run this in a daemon thread).
      - Doesn't spin the CPU when idle.
      - Batches available commands to reduce overhead.
      - Buffers while MQTT reconnects.
    """
    client, connected_evt = connect_mqtt_async(mqtt_port, broker_host_ip)

    buffered: list[str] = []

    try:
        while not shutdown_event.is_set():
            # 1) Drain up to max_batch commands without blocking
            drained = 0
            while drained < max_batch:
                try:
                    cmd = command_queue.get_nowait()
                    buffered.append(cmd)
                    drained += 1
                except queue.Empty:
                    break

            # 2) If connected, publish buffered commands (non-blocking)
            if connected_evt is None or connected_evt.is_set():
                i = 0
                while i < len(buffered):
                    payload = buffered[i]
                    try:
                        info = client.publish(tx_topic, payload=payload, qos=0)
                        # publish is async; check for immediate client-side errors
                        if info.rc != mqtt.MQTT_ERR_SUCCESS:
                            logging.warning("MQTT publish rc=%s; will retry", info.rc)
                            break  # keep remainder buffered; try again next loop
                        i += 1
                    except Exception as exc:
                        logging.exception("Failed to publish MQTT message; will retry: %s", exc)
                        break  # leave remaining buffered

                # Drop successfully sent messages
                if i:
                    del buffered[:i]

            # 3) Idle without busy-waiting (and wake early on shutdown)
            shutdown_event.wait(idle_wait_s)

        # ---- graceful shutdown ----
        # Try to flush remaining buffered commands once more if connected
        if (connected_evt is None or connected_evt.is_set()) and buffered:
            for payload in buffered:
                try:
                    client.publish(tx_topic, payload=payload, qos=0)
                except Exception:
                    break  # best-effort on shutdown

    finally:
        client.loop_stop()  # stops Paho network thread
        try:
            client.disconnect()
        except Exception:
            pass
        logging.info("Commands Worker Thread shutting down")

