import os
import tkinter as tk
from tkinter import ttk
from functions import *
from PIL import Image, ImageTk
import cv2
import globals
import vlc
import threading
import time
from collections import deque


class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
        self.configure(bg="lightgray")
        self.resizable(True, True)

        # Container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}  # store references to frames

        # Initialize all screens
        for F in (DeviceControl, ConnectionSetup, Captures):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Show the DeviceControl screen first
        self.show_frame(DeviceControl)

    def show_frame(self, screen):
        frame = self.frames[screen]
        frame.tkraise()  # bring the frame to the top


class DeviceControl(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        ### instance Variables
        self.fps = 24   # FPS of the stream
        self.buffer_seconds = 30  # how many seconds to keep for save past clip functionality
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)    # where frames for the past clip are stored

        # variables to control the live recording function
        self.recording = False
        self.record_start_time = None
        self.max_record_seconds = 60
        self.recorded_frames = deque(maxlen=self.fps * self.max_record_seconds)
        self.recorded_audio_file = "media/recorded_audio.ogg"
        self.recorded_video_file = "media/recorded_video.mp4"
        self.record_thread = None


        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        connectionsetup_button = tk.Button(
            top_frame, text="Connection Setup",
            command=lambda: controller.show_frame(ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        tk.Button(top_frame, text="Device Control", relief="sunken").pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Captures",
            command=lambda: controller.show_frame(Captures))
        captures_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

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

        # Right panel
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # detect frame
        detect_frame = tk.LabelFrame(right_frame, text="Creatures Detected")
        detect_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        detect_scrollbar = tk.Scrollbar(detect_frame)
        detect_scrollbar.pack(side="right", fill="y")

        detect_listbox = tk.Listbox(detect_frame, yscrollcommand=detect_scrollbar.set)
        detect_listbox.pack(side="left", fill="both", expand=True)

        detect_scrollbar.config(command=detect_listbox.yview)

        creatures = [
            "Platypus", "Lizard", "Crocodile", "Dove",
            "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove"
        ]
        for i in creatures:
            detect_listbox.insert("end", f"{i}")

        # Camera Controls
        cam_frame = tk.LabelFrame(right_frame, text="Camera Controls")
        cam_frame.pack(side="bottom", padx=10, pady=10, fill="x")

        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1, sticky="ew")

        tk.Label(cam_frame, text="Pan:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1, sticky="ew")

        tk.Label(cam_frame, text="Tilt:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=0, to=90, orient="horizontal").grid(row=2, column=1, sticky="ew")

        # tk.Label(cam_frame, text="Volume:").grid(row=3, column=0, sticky="w")
        # self.volume_slider = ttk.Scale(cam_frame, from_=0, to=100, orient="horizontal", command=self.set_volume)
        # self.volume_slider.grid(row=3, column=1, sticky="ew")
        # self.volume_slider.set(50)  # default volume

        cam_frame.grid_columnconfigure(1, weight=1)

        # button frame
        button_frame = tk.Frame(right_frame)
        button_frame.pack(side="top", fill="x")

        self.stream_toggle_button = tk.Button(
            button_frame, text="Start Stream", width=18, bg="white",
            command=lambda: stream_toggle(self))
        
        self.record_button = tk.Button(
            button_frame, text="Start Recording", width=18, command=self.toggle_recording
        )

        tk.Button(button_frame, text="Save last 30s of video", width=18, command=self.save_last_clip).grid(row=0, column=0, sticky="nsew")
        tk.Button(button_frame, text="Save last 30s of Audio", width=18, command=self.record_audio_clip).grid(row=0, column=1, sticky="nsew")
        self.record_button.grid(row=0, column=2, sticky="nsew")
        self.stream_toggle_button.grid(row=1, column=0, sticky="nsew")
        tk.Button(button_frame, text="Audio filter toggle", width=18).grid(row=1, column=1, sticky="nsew")
        tk.Button(button_frame, text="Bounding Box Toggle", width=18).grid(row=1, column=2, sticky="nsew")

        # tk.Button(controls_frame, text="Save 5s", command=self.record_audio_clip, width=12).pack(pady=2)
        # tk.Button(controls_frame, text="Play Stream", command=self.play_audio_stream, width=12).pack(pady=2)
        # tk.Button(controls_frame, text="Stop Stream", command=self.stop_audio_stream, width=12).pack(padx=2)
        
        # --- Audio Section ---
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Left: Audio Visualization
        bottom_left_frame = tk.Frame(bottom_frame)
        bottom_left_frame.pack(side="left", fill="both", expand=True)

        audio_frame = tk.LabelFrame(bottom_left_frame, text="Audio Visualisation")
        audio_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # Right: Audio controls
        bottom_right_frame = tk.Frame(bottom_frame)
        bottom_right_frame.pack(side="right", fill="both")

        audio_controls_frame = tk.Frame(bottom_right_frame)
        audio_controls_frame.pack(side="top", fill="x", padx=10, pady=5)

        self.volume_slider = tk.Scale(
            audio_controls_frame, from_=0, to=100, orient="horizontal",
            label="Volume", command=self.set_volume, length=200
        )
        self.volume_slider.pack(pady=2, fill="x", expand=True)
        self.volume_slider.set(50)  # default volume

        # VLC player instance
        self.instance = vlc.Instance('--quiet')
        self.player = self.instance.media_player_new()

        # Audio Stream stuff
        self.is_playing = False
        self.AUDIO_OUTPUT_FILE = "media/audio_clip.ogg"

        
    def play_audio_stream(self):
        media = self.instance.media_new(globals.audio_url)
        self.player.set_media(media)
        self.player.audio_set_volume(self.volume_slider.get())  # apply slider setting
        self.player.play()


    def stop_audio_stream(self):
        self.player.stop()


    def set_volume(self, value):
        self.player.audio_set_volume(int(value))


    def record_audio_clip(self):
        def _record():
            if os.path.exists(self.AUDIO_OUTPUT_FILE):
                os.remove(self.AUDIO_OUTPUT_FILE)
            options = f":sout=#file{{dst={self.AUDIO_OUTPUT_FILE}}}"
            media = self.instance.media_new(globals.audio_url, options)
            recorder = self.instance.media_player_new()
            recorder.set_media(media)
            recorder.play()
            time.sleep(5)
            recorder.stop()
            print(f"Saved 5s clip to {self.AUDIO_OUTPUT_FILE}")

        threading.Thread(target=_record, daemon=True).start()


    def save_last_clip(self):
        if not self.frame_buffer:
            print("No frames in buffer!")
            return 0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter("media/video_clip.mp4", fourcc, self.fps,
                              (self.frame_buffer[0].shape[1], self.frame_buffer[0].shape[0]))
        for f in list(self.frame_buffer):
            out.write(f)
        out.release()
        print("Saved last 30 seconds of video to video_clip.mp4")
        return 1
    
    
    # Live Recording Functions
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            self.recording = True
            self.record_start_time = time.time()
            self.recorded_frames.clear()

            # Start background thread to record video + audio
            self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.record_thread.start()

            self.record_button.config(bg="red", text="Stop Recording")
            print("Recording started")
        else:
            # Stop recording
            self.recording = False
            self.record_button.config(bg="white", text="Start Recording")
            print("Recording stopped")
            self._save_recording()


    def _record_loop(self):
        """
        Background loop to capture video frames and audio while recording.
        Stops automatically after self.max_record_seconds.
        """
        # Optional: Record audio via VLC stream
        options = f":sout=#file{{dst={self.recorded_audio_file}}}"
        media = self.instance.media_new(globals.audio_url, options)
        recorder = self.instance.media_player_new()
        recorder.set_media(media)
        recorder.play()

        while self.recording:
            if self.frame_buffer:
                self.recorded_frames.append(self.frame_buffer[-1].copy())
            if time.time() - self.record_start_time >= self.max_record_seconds:
                self.recording = False
                break
            time.sleep(1 / self.fps)  # sync to frame rate

        recorder.stop()
        self._save_recording()


    def _save_recording(self):
        if not self.recorded_frames:
            print("No frames recorded!")
            return

        # Save video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        height, width = self.recorded_frames[0].shape[:2]
        out = cv2.VideoWriter(self.recorded_video_file, fourcc, self.fps, (width, height))
        for f in self.recorded_frames:
            out.write(f)
        out.release()
        print(f"Video saved to {self.recorded_video_file}")

        # Audio is already saved by VLC to self.recorded_audio_file
        print(f"Audio saved to {self.recorded_audio_file}")


class Captures(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        connectionsetup_button = tk.Button(
            top_frame, text="Connection Setup",
            command=lambda: controller.show_frame(ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Device Control",
            command=lambda: controller.show_frame(DeviceControl))
        captures_button.pack(side="left", padx=5)

        tk.Button(top_frame, text="Captures", relief="sunken").pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        files_tree = ttk.Treeview(main_frame, columns=("time", "size", "type"), show="tree headings")
        files_tree.pack(fill="both", expand=True, padx=20, pady=20)

        files_tree.heading("#0", text="File Name", anchor="w")
        files_tree.heading("size", text="Size", anchor="w")
        files_tree.heading("type", text="Type", anchor="w")
        files_tree.heading("time", text="Last Modified", anchor="w")

        files_tree.column("#0", width=200)
        files_tree.column("size", width=100)
        files_tree.column("type", width=80)
        files_tree.column("time", width=150)

        media_dir = "./media"
        populate_tree(media_dir, files_tree, ALL_EXTS)
        files_tree.bind("<Double-1>", lambda event: tree_open_file(event, media_dir, files_tree))


class ConnectionSetup(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        tk.Button(top_frame, text="Connection Setup", relief="sunken").pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Device Control",
            command=lambda: controller.show_frame(DeviceControl))
        captures_button.pack(side="left", padx=5)

        connectionsetup_button = tk.Button(
            top_frame, text="Captures",
            command=lambda: controller.show_frame(Captures))
        connectionsetup_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        connection_main_frame = tk.Frame(self)
        connection_main_frame.pack(fill="both", expand=True)

        info_frame = tk.LabelFrame(connection_main_frame, text="Connection Information")
        info_frame.pack(side="top", padx=100, pady=50, fill="both", expand=True)

        self.video_url_text = tk.Entry(info_frame)
        self.video_url_text.pack(fill="x", padx=10, pady=10)
        self.video_url_text.insert(0, globals.video_url)

        self.title = tk.Label(connection_main_frame, text="")
        self.title.pack(side="top")

        connect_button = tk.Button(
            connection_main_frame, text="Connect to Stream", command=lambda: set_link(self))
        connect_button.pack(side="top", pady=100)


if __name__ == "__main__":
    app = WildlifeBotApp()
    app.state("zoomed")  # start full screen on Windows; use app.attributes("-fullscreen", True) for Linux
    app.mainloop()
