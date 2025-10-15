import os
import time
import wave
import socket
import threading
import datetime
from collections import deque

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

import cv2
import vlc
import numpy as np
import pyaudio
import requests
import sounddevice as sd  # (unused in current flow; kept to preserve original imports)

from ultralytics import YOLO
from webRTCmultiporcessing import WebRTCStream

import globals
from functions import *  # noqa: F401,F403  (kept as-is per original)
from headless_controller import HeadlessController
from high_accuracy_classifier import HighAccuracyAnimalClassifier  # lazy-imported again in _init_audio_classifier


# ---------------------------------------------------------------------
# Module-level defaults (preserved)
# ---------------------------------------------------------------------
pan_angle = 45   # start at middle
tilt_angle = 0
crane_angle = 0


class DeviceControl(tk.Frame):
    """
    Main GUI frame handling:
      - Video stream (WebRTC) with optional YOLO overlay
      - Rolling buffers for audio/video + manual recording
      - Torch/AWB controls via HTTP requests
      - Arrow-key gimbal control via HeadlessController
      - Audio classification with voting window and GUI log
    """

    # ------------------------
    # Construction & UI
    # ------------------------
    def __init__(self, parent):
        super().__init__(parent)

        # ---- Paths / Media ----
        self.recorded_audio_file = "media/recorded_audio.ogg"
        self.buffer_audio_clip_file = "media/buffer_audio.wav"
        self.recorded_video_file = "media/recorded_video.mp4"

        # Ensure media directories exist
        os.makedirs("media", exist_ok=True)
        os.makedirs("media/audio_detections", exist_ok=True)
        os.makedirs("media/recordings/audio", exist_ok=True)
        os.makedirs("media/recordings/video", exist_ok=True)
        os.makedirs("media/visual_detections", exist_ok=True)

        # ---- Video stream settings ----
        self.fps = 24
        self.buffer_seconds = 30
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)

        # ---- Audio stream (UDP PCM) ----
        self.AUDIO_IP = "0.0.0.0"
        self.AUDIO_PORT = 5004
        self.AUDIO_CHUNK_SIZE = 1024
        self.AUDIO_FORMAT = pyaudio.paInt16
        self.AUDIO_CHANNELS = 1
        self.AUDIO_RATE = 44100

        self.volume_level = 1.0

        # Rolling audio buffer
        self.audio_buffer_seconds = 30
        self.audio_sample_rate = 44100
        self.audio_channels = self.AUDIO_CHANNELS  # keep in sync
        # initialize then overwrite to match self.AUDIO_RATE / CHUNK sizing (preserved behavior)
        self.audio_buffer = deque(maxlen=self.audio_buffer_seconds * self.audio_sample_rate // 1024)
        self.audio_stream_process = None
        self.audio_buffer = deque(maxlen=self.audio_buffer_seconds * self.AUDIO_RATE // (self.AUDIO_CHUNK_SIZE * 4))

        # Collects audio chunks during manual recording
        self.audio_recording = []

        # ---- Audio classifier (initialized in background) ----
        self.audio_classifier = None
        self.classification_enabled = False

        # Voting summary / spam control
        self.detected_animals = {}
        self.last_announced_animal = None

        # Key handling cooldown (kept but not used elsewhere)
        self.last_key_time = 0
        self.key_cooldown = 0.1

        # ---- Manual recording (video) ----
        self.recording = False
        self.record_start_time = None
        self.max_record_seconds = 60
        self.recorded_frames = deque(maxlen=self.fps * self.max_record_seconds)

        # ---- Camera/processing toggles ----
        self.torch_1 = tk.BooleanVar(value=False)
        self.torch_2 = tk.BooleanVar(value=False)
        self.awb_enabled = tk.BooleanVar(value=False)

        # ---- WebRTC & Controller ----
        self.webrtc_client = WebRTCStream("http://192.168.212.90:8889/cam")
        self.webrtc_loop = None
        self.webrtc_connection_future = None
        self.webrtc_close_future = None

        self.command_controller = HeadlessController(
            mqtt_broker_host_ip=globals.controller_IP.split(":")[0],
            mqtt_port=int(globals.controller_IP.split(":")[1]),
        )

        # ---- YOLO ----
        self.yolo_model: YOLO = YOLO("best.pt")
        self.toggle_model = False

        # ---- Logs for audio classification ----
        self.logs_dir = os.path.join(os.getcwd(), "logs", "audio")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.gui_log_path = os.path.join(self.logs_dir, "gui_audio_top1.log")
        if not os.path.exists(self.gui_log_path):
            try:
                with open(self.gui_log_path, "a") as f:
                    f.write(f"# GUI Audio Top-1 Log - started {datetime.datetime.now().isoformat()}\n")
            except Exception:
                pass

        # Initialize audio classifier in a background thread
        threading.Thread(target=self._init_audio_classifier, daemon=True).start()

        # Build UI
        self.layout()

    def layout(self):
        """Builds the GUI layout and binds events."""
        # --- Video + Controls section ---
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left video frame
        self.video_frame = tk.LabelFrame(main_frame, text="Camera View")
        self.video_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.video_label = tk.Label(self.video_frame, bd=1, relief="groove")
        self.video_label.pack(fill="both", expand=True, padx=10, pady=10)
        img = Image.open("stream_standby_image.jpg").resize((600, 400))
        self.stream_standby_photo = ImageTk.PhotoImage(img)
        self.video_label.config(image=self.stream_standby_photo)

        # Servo key controls
        self.video_label.focus_set()
        self.video_label.bind("<KeyPress>", self.keydown)
        self.video_label.bind("<KeyRelease>", self.keyup)
        self.video_label.bind("<Button-1>", lambda e: self.video_label.focus_set())

        # Right panel
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # Detected creatures
        detect_frame = tk.LabelFrame(right_frame, text="Creatures Detected")
        detect_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        detect_scrollbar = tk.Scrollbar(detect_frame)
        detect_scrollbar.pack(side="right", fill="y")

        self.detect_listbox = tk.Listbox(detect_frame, yscrollcommand=detect_scrollbar.set)
        self.detect_listbox.pack(side="left", fill="both", expand=True)
        detect_scrollbar.config(command=self.detect_listbox.yview)

        # Initial load message for classifier
        self.detect_listbox.insert("end", "Audio classifier loading...")
        self.detect_listbox.insert("end", "Please wait...")

        # Audio classification toggle
        audio_controls_frame = tk.Frame(detect_frame)
        audio_controls_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        self.audio_classification_button = tk.Button(
            audio_controls_frame,
            text="Start Audio Detection",
            command=self.toggle_audio_classification,
            state=tk.DISABLED,  # enabled once classifier loads
        )
        self.audio_classification_button.pack(side="left", padx=5)

        # Camera Controls
        cam_frame = tk.LabelFrame(right_frame, text="Camera Controls")
        cam_frame.pack(side="bottom", padx=10, pady=10, fill="x")
        cam_frame.columnconfigure(0, weight=1)
        cam_frame.columnconfigure(1, weight=1)
        cam_frame.columnconfigure(2, weight=1)

        tk.Label(cam_frame, text="Pan:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1, sticky="ew")

        tk.Label(cam_frame, text="Tilt:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=0, to=90, orient="horizontal").grid(row=2, column=1, sticky="ew")

        def torch_1_control():
            try:
                requests.get(
                    f"http://{globals.PI_IP}:5000/torch",
                    params={"torch_1": 1 if not self.torch_1.get() else 0},
                    timeout=10,
                )
                self.torch_1.set(not self.torch_1.get())
                btn_torch_1.config(text=f"Torch 1: {'ON' if self.torch_1.get() else 'OFF'}")
            except requests.Timeout:
                print("Request timed out - Torch 1.")

        def torch_2_control():
            try:
                requests.get(
                    f"http://{globals.PI_IP}:5000/torch",
                    params={"torch_2": 1 if not self.torch_2.get() else 0},
                    timeout=10,
                )
                self.torch_2.set(not self.torch_2.get())
                # fixed label text
                btn_torch_2.config(text=f"Torch 2: {'ON' if self.torch_2.get() else 'OFF'}")
            except requests.Timeout:
                print("Request timed out - Torch 2.")

        def awb_control():
            self.awb_enabled.set(not self.awb_enabled.get())
            btn_awb.config(text=f"AWB: {'ON' if self.awb_enabled.get() else 'OFF'}")

        btn_torch_1 = tk.Button(cam_frame, text=f"Torch 1: {'ON' if self.torch_1.get() else 'OFF'}", command=torch_1_control)
        btn_torch_1.grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        btn_torch_2 = tk.Button(cam_frame, text=f"Torch 2: {'ON' if self.torch_2.get() else 'OFF'}", command=torch_2_control)
        btn_torch_2.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        btn_awb = tk.Button(cam_frame, text=f"AWB: {'ON' if self.awb_enabled.get() else 'OFF'}", command=awb_control)
        btn_awb.grid(row=3, column=2, sticky="ew", padx=5, pady=5)

        cam_frame.grid_columnconfigure(1, weight=1)

        # Buttons (stream/record/etc)
        button_frame = tk.Frame(right_frame)
        button_frame.pack(side="top", fill="x", expand=True)

        self.stream_toggle_button = tk.Button(
            button_frame, text="Start Stream", width=18, bg="white", command=lambda: self.stream_toggle()
        )
        self.record_button = tk.Button(button_frame, text="Start Recording", width=18, command=self.toggle_recording)

        tk.Button(button_frame, text="Save last 30s of video", width=18, command=self.save_last_video).grid(
            row=0, column=0, sticky="nsew"
        )
        tk.Button(button_frame, text="Save last 30s of Audio", width=18, command=self.save_last_audio).grid(
            row=0, column=1, sticky="nsew"
        )
        self.record_button.grid(row=0, column=2, sticky="nsew")
        self.stream_toggle_button.grid(row=1, column=0, sticky="nsew")

        self.controller_button = tk.Button(
            button_frame,
            text="Start Controls",
            width=18,
            command=lambda: self.command_controller.start_loop(),
        )
        self.controller_button.grid(row=1, column=1, sticky="nsew")

        def toggle_yolo():
            self.toggle_model = not self.toggle_model
            btn_yolo.config(text=f"YOLO Model: {'ON' if self.toggle_model else 'OFF'}")

        btn_yolo = tk.Button(button_frame, text="Bounding Box Toggle", width=18, command=toggle_yolo)
        btn_yolo.grid(row=1, column=2, sticky="nsew")

        # --- Audio Section (bottom) ---
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        bottom_left_frame = tk.Frame(bottom_frame)
        bottom_left_frame.pack(side="left", fill="both", expand=True)

        audio_frame = tk.LabelFrame(bottom_left_frame, text="Audio Visualisation")
        audio_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        bottom_right_frame = tk.Frame(bottom_frame)
        bottom_right_frame.pack(side="right", fill="both")

        audio_controls_frame = tk.Frame(bottom_right_frame)
        audio_controls_frame.pack(side="top", fill="x", padx=10, pady=5)

        self.volume_slider = tk.Scale(
            audio_controls_frame, from_=0, to=100, orient="horizontal", label="Volume", command=self.set_volume, length=200
        )
        self.volume_slider.pack(pady=2, fill="x", expand=True)
        self.volume_slider.set(50)

        # VLC objects now initialized (were commented out previously)
        try:
            self.instance = vlc.Instance("--quiet --network-caching=0")
            self.player = self.instance.media_player_new()
        except Exception:
            self.instance = None
            self.player = None

    # ------------------------
    # Helpers
    # ------------------------
    def _name_output_file(self, filename: str) -> str:
        """
        Helper to add timestamp before the extension.
        Example: "media/video.mp4" -> "media/video_YYYY-MM-DD HH-MM-SS.mp4"
        """
        root, ext = os.path.splitext(filename)
        return f"{root}_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H-%M-%S')}{ext}"

    def set_volume(self, value):
        """Set audio volume for VLC player (if initialized)."""
        try:
            if getattr(self, "player", None):
                self.player.audio_set_volume(int(value))
        except Exception:
            pass  # keep original permissive behavior

    # ------------------------
    # Video buffer & recording
    # ------------------------
    def save_last_video(self):
        """Save the last 30s of frames from rolling buffer to mp4."""
        output_file = self._name_output_file("media/video_clip.mp4")
        if not self.frame_buffer:
            print("No frames in buffer!")
            return 0

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            output_file,
            fourcc,
            self.fps,
            (self.frame_buffer[0].shape[1], self.frame_buffer[0].shape[0]),
        )
        for f in list(self.frame_buffer):
            out.write(f)
        out.release()
        print(f"Saved last 30 seconds of video to {output_file}")
        return 1

    def toggle_recording(self):
        """Start/stop manual recording (video + audio)."""
        if not self.recording:
            # Start recording
            self.recording = True
            self.record_start_time = time.time()
            self.recorded_frames.clear()

            # Start the audio recorder (guard if VLC not ready)
            try:
                if getattr(self, "instance", None):
                    output_file = self._name_output_file(self.recorded_audio_file)
                    options = f":sout=#file{{dst={output_file}}}"
                    self._rec_media = self.instance.media_new(globals.audio_url, options)
                    self._rec_player = self.instance.media_player_new()
                    self._rec_player.set_media(self._rec_media)
                    self._rec_player.play()
            except Exception:
                pass

            # Visual cue
            self.record_button.config(bg="red", text="Stop Recording")
            print("Recording started")

            # Kick off the self-calling tick
            self._record_tick()
        else:
            # Stop recording
            self.recording = False
            self.record_button.config(bg="white", text="Start Recording")
            print("Recording stopped")
            try:
                if hasattr(self, "_rec_player") and self._rec_player:
                    self._rec_player.stop()
            except Exception:
                pass
            self._save_video_recording()

    def _record_tick(self):
        """
        Self-calling tick to capture frames during manual recording.
        Uses tk.after to avoid a while loop.
        """
        if not self.recording:
            return

        if self.frame_buffer:
            self.recorded_frames.append(self.frame_buffer[-1].copy())

        # Stop if we've reached the recording limit
        if time.time() - self.record_start_time >= self.max_record_seconds:
            self.recording = False
            # toggle_recording() will handle stopping + saving
            self.toggle_recording()
            print("recording limit reached")
            return

        # Schedule next tick
        self.after(int(1000 / self.fps), self._record_tick)

    def _save_video_recording(self):
        """Write collected frames from manual recording to file."""
        if not self.recorded_frames:
            print("No frames recorded!")
            return

        output_file = self._name_output_file(self.recorded_video_file)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        height, width = self.recorded_frames[0].shape[:2]
        out = cv2.VideoWriter(output_file, fourcc, self.fps, (width, height))
        for f in self.recorded_frames:
            out.write(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        out.release()

    # ------------------------
    # Audio rolling buffer save
    # ------------------------
    def save_last_audio(self, N=30, folder=None, filename=None):
        """
        Save the last N seconds of audio from the buffer to a WAV file.
        """
        if N > 30 or N < 0:
            print("Invalid N, returning to default")
            N = 30

        folder = folder or "recordings/audio"
        filename = filename or "buffer_audio"

        if not self.audio_buffer:
            print("No audio in buffer!")
            return

        slice_index = int(len(self.audio_buffer) * (N / 30))
        data = b"".join(list(self.audio_buffer)[:slice_index])
        pcm_data = np.frombuffer(data, dtype=np.int16)

        out_dir = os.path.join("media", folder)
        os.makedirs(out_dir, exist_ok=True)
        write_file = os.path.join(out_dir, self._name_output_file(filename + "_") + ".wav")

        with wave.open(write_file, "wb") as wf:
            wf.setnchannels(self.AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.AUDIO_RATE)
            wf.writeframes(pcm_data.tobytes())

        print(f"Saved last {N} seconds of audio to {write_file}")

    # ------------------------
    # Stream control (video + UDP audio)
    # ------------------------
    def stream_toggle(self):
        """Start/stop WebRTC video and UDP audio streaming."""

        def gray_world_awb(img):
            img_float = img.astype(np.float32)
            avg_b = np.mean(img_float[:, :, 0])
            avg_g = np.mean(img_float[:, :, 1])
            avg_r = np.mean(img_float[:, :, 2])
            avg_gray = (avg_b + avg_g + avg_r) / 3
            img_float[:, :, 0] *= (avg_gray / avg_b)
            img_float[:, :, 1] *= (avg_gray / avg_g)
            img_float[:, :, 2] *= (avg_gray / avg_r)
            return np.clip(img_float, 0, 255).astype(np.uint8)

        def video_loop():
            if not globals.streaming:
                print("Video loop: Not streaming, exiting video loop")
                return

            frame = self.webrtc_client.get_frame()

            # keep ticking even if empty frame
            if frame is None:
                print("No frame received")
                self.video_label.after(20, video_loop)
                return

            if self.toggle_model:
                results = self.yolo_model(frame, conf=0.5)

            if self.awb_enabled.get():
                frame = gray_world_awb(frame)

            if self.toggle_model:
                annotated_frame = results[0].plot()
                frame = annotated_frame

            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

            self.frame_buffer.append(frame.copy())
            self.video_label.after(20, video_loop)

        if not globals.streaming:
            # ----- START STREAM -----
            globals.streaming = True
            self.stream_toggle_button.config(text="Stop Stream")

            self.webrtc_client.set_stream_link(globals.video_url)
            self.webrtc_client.start_connection()

            if not self.webrtc_client.is_connected():
                print("WebRTC Connection failed, restarting thread")
                globals.streaming = False
                self.stream_toggle_button.config(text="Start Stream")
                self.webrtc_client.close_thread()
                return

            # start the video tick
            video_loop()

            # --- UDP audio setup (non-blocking) ---
            self.audio_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_sock.bind((self.AUDIO_IP, self.AUDIO_PORT))
            self.audio_sock.setblocking(False)

            p = pyaudio.PyAudio()
            self.audio_stream = p.open(
                format=self.AUDIO_FORMAT,
                channels=self.AUDIO_CHANNELS,
                rate=self.AUDIO_RATE,
                output=True,
                frames_per_buffer=self.AUDIO_CHUNK_SIZE,
            )

            # Kick off the self-calling audio tick
            self._audio_stream_tick()

        else:
            # ----- STOP STREAM -----
            globals.streaming = False
            try:
                self.webrtc_client.stop_connection()
            finally:
                self.stream_toggle_button.config(text="Start Stream")
                self.video_label.config(image=self.stream_standby_photo)

                # Close audio resources if present
                try:
                    if getattr(self, "audio_stream", None):
                        self.audio_stream.stop_stream()
                        self.audio_stream.close()
                        self.audio_stream = None
                except Exception:
                    pass
                try:
                    if getattr(self, "audio_sock", None):
                        self.audio_sock.close()
                        self.audio_sock = None
                except Exception:
                    pass
                print("WebRTC connection closed.")

    def _audio_stream_tick(self):
        """
        Self-calling tick to pull a UDP audio packet (non-blocking) and play it.
        Avoids while True; reschedules itself while streaming is True.
        """
        if not globals.streaming:
            return

        try:
            # Try read one packet (non-blocking); OK if none available
            data, _ = self.audio_sock.recvfrom(self.AUDIO_CHUNK_SIZE * 32)
            self.audio_buffer.append(data)

            if self.recording:
                self.audio_recording.append(data)

            audio_bytes = np.frombuffer(data, dtype=np.int16)
            adjusted = (audio_bytes * self.volume_level).astype(np.int16)
            self.audio_stream.write(adjusted.tobytes())
        except (BlockingIOError, socket.error):
            # No packet ready or transient read error; just skip this tick
            pass
        except Exception as e:
            print(f"Audio tick error: {e}")

        # Recur quickly to approximate continuous audio
        threading.Timer(0.005, self._audio_stream_tick).start()  # ~5ms cadence

    def stop_video_stream(self):
        """Stop OpenCV VideoCapture (legacy path, preserved)."""
        globals.capture.release()

    # ------------------------
    # Key bindings (gimbal)
    # ------------------------
    def keyup(self, e):
        state_change = False

        if e.keysym == "Up" and globals.upKeyState:
            globals.upKeyState = False
            state_change = True
        elif e.keysym == "Down" and globals.downKeyState:
            globals.downKeyState = False
            state_change = True
        elif e.keysym == "Left" and globals.leftKeyState:
            globals.leftKeyState = False
            state_change = True
        elif e.keysym == "Right" and globals.rightKeyState:
            globals.rightKeyState = False
            state_change = True
        elif e.keysym == "apostrophe" and globals.apostropheState:
            globals.apostropheState = False
            state_change = True
        elif e.keysym == "slash" and globals.slashState:
            globals.slashState = False
            state_change = True

        if state_change:
            print(e.keysym, "released")

    def keydown(self, e):
        global pan_angle, tilt_angle, crane_angle

        state_change = False
        if e.keysym == "Up" and not globals.upKeyState:
            globals.upKeyState = True
            state_change = True
            try:
                tilt_angle = max(tilt_angle - 10, 0)
                print(f"tilt angle {tilt_angle}")
                self.command_controller.send_gimbal_command("y", tilt_angle)
            except Exception:
                pass

        elif e.keysym == "Down" and not globals.downKeyState:
            globals.downKeyState = True
            state_change = True
            try:
                tilt_angle = min(tilt_angle + 10, 90)
                print(f"tilt angle {tilt_angle}")
                self.command_controller.send_gimbal_command("y", tilt_angle)
            except Exception:
                pass

        elif e.keysym == "Left" and not globals.leftKeyState:
            globals.leftKeyState = True
            state_change = True
            try:
                pan_angle = min(pan_angle + 5, 90)
                print(f"pan angle {pan_angle}")
                self.command_controller.send_gimbal_command("x", pan_angle)
            except Exception:
                pass

        elif e.keysym == "Right" and not globals.rightKeyState:
            globals.rightKeyState = True
            state_change = True
            try:
                pan_angle = max(pan_angle - 5, 0)
                print(f"pan angle {pan_angle}")
                self.command_controller.send_gimbal_command("x", pan_angle)
            except Exception:
                pass

        elif e.keysym == "apostrophe" and not globals.apostropheState:
            globals.apostropheState = True
            state_change = True
            try:
                crane_angle = min(crane_angle + 10, 90)
                print(f"crane angle {crane_angle}")
                self.command_controller.send_gimbal_command("c", crane_angle)
            except Exception:
                pass

        elif e.keysym == "slash" and not globals.slashState:
            globals.slashState = True
            state_change = True
            try:
                crane_angle = max(crane_angle - 10, 0)
                print(f"crane angle {crane_angle}")
                self.command_controller.send_gimbal_command("c", crane_angle)
            except Exception:
                pass

        if state_change:
            print(e.keysym, "pressed")

    # ------------------------
    # Audio classification
    # ------------------------
    def _init_audio_classifier(self):
        """Initialize the audio classifier in a background thread."""
        try:
            print("Initializing audio classifier...")

            # Lazy import to mirror original intent (avoids TF init at startup)
            from high_accuracy_classifier import HighAccuracyAnimalClassifier  # noqa: F811

            model_path = os.path.join("models", "animal_classifier_best.h5")
            if not os.path.exists(model_path):
                print(f"Warning: Model file '{model_path}' not found!")
                self.after(0, self._update_classifier_status, "Model file not found")
                return

            self.audio_classifier = HighAccuracyAnimalClassifier()
            self.after(0, self._update_classifier_status, "CRNN classifier ready ✅")
            print("CRNN audio classifier initialized successfully!")

        except Exception as e:
            print(f"Error initializing audio classifier: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, self._update_classifier_status, f"Error: {str(e)}")

    def _update_classifier_status(self, message):
        """Update UI with classifier status (on main thread)."""
        self.detect_listbox.delete(0, tk.END)
        self.detect_listbox.insert("end", message)
        if self.audio_classifier is not None:
            self.audio_classification_button.config(state=tk.NORMAL)

    def toggle_audio_classification(self):
        """Start/stop audio classification loop."""
        if self.audio_classifier is None:
            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "Audio classifier not ready")
            return

        if not self.classification_enabled:
            self.classification_enabled = True
            self.audio_classification_button.config(text="Stop Audio Detection", bg="red")

            self.detected_animals = {}
            self.last_announced_animal = None
            if self.audio_classifier:
                self.audio_classifier.reset_voting_history()

            self._classification_tick()

            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "   Audio detection started!")
            self.detect_listbox.insert("end", "   Analyzing every 3 seconds...")
            self.detect_listbox.insert("end", "   Voting window: 30 seconds (10 predictions)")
            self.detect_listbox.insert("end", "   Detection requires 70% vote agreement")
            print("CRNN audio classification started (3-second intervals with voting)")
        else:
            self.classification_enabled = False
            self.audio_classification_button.config(text="Start Audio Detection", bg="SystemButtonFace")

            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "🛑 Audio detection stopped")

            if self.detected_animals:
                self.detect_listbox.insert("end", "")
                self.detect_listbox.insert("end", "📊 Session Summary:")
                sorted_detections = sorted(self.detected_animals.items(), key=lambda x: x[1], reverse=True)
                for animal, count in sorted_detections:
                    self.detect_listbox.insert("end", f"   {animal}: {count} confirmed detections")

            print("Audio classification stopped")

    def _classification_tick(self):
        """Self-calling tick for continuous audio classification with voting."""
        if not (self.classification_enabled and self.audio_classifier is not None):
            return

        try:
            if len(self.audio_buffer) > 0:
                # ~3 seconds at 44100 Hz
                samples_needed = int(3.0 * self.audio_sample_rate)

                raw_audio_data = b"".join(self.audio_buffer)
                audio_data = np.frombuffer(raw_audio_data, dtype=np.float32)

                if len(audio_data) > samples_needed:
                    audio_data = audio_data[-samples_needed:]

                if self.audio_channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1)
                else:
                    audio_data = audio_data.flatten()

                audio_magnitude = np.max(np.abs(audio_data))

                if audio_magnitude > 0.01:
                    result = self.audio_classifier.predict_with_voting(
                        audio_data,
                        source_sample_rate=self.audio_sample_rate,
                    )
                    self.after(0, self._update_detections, result)
                else:
                    self.after(0, self._update_detections_silence)

        except Exception as e:
            print(f"Error in classification tick: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, self._update_detections_error, str(e))

        # Recur in ~3 seconds
        threading.Timer(3.0, self._classification_tick).start()

    def _update_detections(self, result):
        """
        Update the listbox with top predictions and voting progress.
        result: dict with 'current' (list of tuples) and 'voting' (dict)
        """
        if not self.classification_enabled:
            return

        current_predictions = result.get("current", [])
        voting_info = result.get("voting", {})

        voted_animal = voting_info.get("prediction")
        vote_pct = voting_info.get("vote_percentage", 0.0)
        avg_conf = voting_info.get("avg_confidence", 0.0)
        is_confident = voting_info.get("is_confident", False)

        self.detect_listbox.delete(0, tk.END)

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.detect_listbox.insert("end", f"🕒 {timestamp} - Audio Analysis (3s):")
        self.detect_listbox.insert("end", "=" * 45)

        self.detect_listbox.insert("end", "📊 Current Prediction:")
        for i, (animal, confidence) in enumerate(current_predictions[:3], 1):
            confidence_percent = confidence * 100
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            display_text = f"{emoji} #{i}: {animal:<15} ({confidence_percent:5.1f}%)"
            self.detect_listbox.insert("end", display_text)

        self.detect_listbox.insert("end", "=" * 45)

        if voted_animal:
            self.detect_listbox.insert("end", "🗳️  Voting Window (30s):")
            bar_length = 20
            filled = int(bar_length * vote_pct)
            bar = "█" * filled + "░" * (bar_length - filled)
            self.detect_listbox.insert("end", f"   {voted_animal}:")
            self.detect_listbox.insert("end", f"   [{bar}] {vote_pct*100:.0f}%")
            self.detect_listbox.insert("end", f"   Confidence: {avg_conf*100:.1f}%")

            if is_confident:
                self.detect_listbox.insert("end", "")
                self.detect_listbox.insert("end", "✅ ANIMAL DETECTED! ✅")
                self.detect_listbox.insert("end", f"🎯 {voted_animal}")
                self.detect_listbox.insert("end", "")

                if voted_animal not in self.detected_animals:
                    self.detected_animals[voted_animal] = 0
                self.detected_animals[voted_animal] += 1

                if self.last_announced_animal != voted_animal:
                    print(f"\n{'='*60}")
                    print(f"🚨 NEW ANIMAL DETECTED: {voted_animal} 🚨")
                    print(f"   Vote: {vote_pct*100:.0f}% | Confidence: {avg_conf*100:.1f}%")
                    print(f"{'='*60}\n")
                    self.last_announced_animal = voted_animal

                    try:
                        if hasattr(self, "gui_log_path") and self.gui_log_path:
                            with open(self.gui_log_path, "a") as f:
                                f.write(
                                    f"{datetime.datetime.now().isoformat()} - DETECTION: {voted_animal} "
                                    f"(Vote: {vote_pct*100:.0f}%, Conf: {avg_conf*100:.1f}%)\n"
                                )
                    except Exception:
                        pass
            else:
                import config
                needed_pct = config.VOTING_THRESHOLD * 100
                self.detect_listbox.insert("end", f"   ⏳ Need {needed_pct:.0f}% to confirm")
        else:
            self.detect_listbox.insert("end", "🗳️  Voting Window: Empty")
            self.detect_listbox.insert("end", "   Waiting for predictions...")

        self.detect_listbox.insert("end", "=" * 45)

        if self.detected_animals:
            self.detect_listbox.insert("end", "📋 Confirmed Detections:")
            sorted_detections = sorted(self.detected_animals.items(), key=lambda x: x[1], reverse=True)
            for animal, count in sorted_detections[:5]:
                self.detect_listbox.insert("end", f"   ✓ {animal}: {count}x")

        self.detect_listbox.see(tk.END)

        if is_confident:
            log_msg = f"DETECTED: {voted_animal} (Vote: {vote_pct*100:.0f}%, Conf: {avg_conf*100:.1f}%)"
        else:
            top = current_predictions[0] if current_predictions else ("None", 0.0)
            log_msg = f"Current: {top[0]} ({top[1]*100:.1f}%) | Voting: {voted_animal or 'None'} ({vote_pct*100:.0f}%)"
        print(f"Audio: {log_msg}")

    def _update_detections_silence(self):
        """No-op UI update when input is effectively silent."""
        pass

    def _update_detections_error(self, error_msg):
        """UI update when classification errors occur."""
        if not self.classification_enabled:
            return
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.detect_listbox.delete(0, tk.END)
        self.detect_listbox.insert("end", f"🕒 {timestamp} (3s interval)")
        self.detect_listbox.insert("end", f"❌ Error: {error_msg}")
        self.detect_listbox.insert("end", "Retrying in 3 seconds...")
