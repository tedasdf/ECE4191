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
import datetime
from collections import deque

import sounddevice as sd
import numpy as np
import wave


class DeviceControl(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        ### instance Variables
        self.fps = 24   # FPS of the stream
        self.buffer_seconds = 30  # how many seconds to keep for save past clip functionality
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)    # where frames for the past clip are stored

        # audio buffer stuff
        # Audio Stream stuff
        self.AUDIO_OUTPUT_FILE = f"media/recorded_audio.ogg"

        # self.audio_temp_file = "media/temp_audio.ogg"

        self.audio_buffer_seconds = 30  # how many seconds to keep
        self.audio_sample_rate = 44100
        self.audio_channels = 2
        self.audio_buffer = deque(maxlen=self.audio_buffer_seconds * self.audio_sample_rate // 1024)  # 1024-frame chunks
        self.last_audio_clip_file = f"media/recorded_audio.wav"

        # Start the audio capture in a background thread
        threading.Thread(target=self._audio_capture_loop, daemon=True).start()


        # variables to control the live recording function
        self.recording = False
        self.record_start_time = None
        self.max_record_seconds = 60
        self.recorded_frames = deque(maxlen=self.fps * self.max_record_seconds)
        self.recorded_audio_file = f"media/recorded_audio.ogg"
        self.recorded_video_file = f"media/recorded_video.mp4"
        self.record_thread = None


        # # --- Top Menu Bar ---
        # top_frame = tk.Frame(self, bg="white", pady=5)
        # top_frame.pack(fill="x")

        # logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        # logo.pack(side="left", padx=10)

        # connectionsetup_button = tk.Button(
        #     top_frame, text="Connection Setup",
        #     command=lambda: controller.show_frame(ConnectionSetup))
        # connectionsetup_button.pack(side="left", padx=5)

        # tk.Button(top_frame, text="Device Control", relief="sunken").pack(side="left", padx=5)

        # captures_button = tk.Button(
        #     top_frame, text="Captures",
        #     command=lambda: controller.show_frame(Captures))
        # captures_button.pack(side="left", padx=5)

        # tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

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

        cam_frame.grid_columnconfigure(1, weight=1)

        # button frame
        button_frame = tk.Frame(right_frame)
        button_frame.pack(side="top", fill="x", expand=True)

        self.stream_toggle_button = tk.Button(
            button_frame, text="Start Stream", width=18, bg="white",
            command=lambda: stream_toggle(self))
        
        self.record_button = tk.Button(
            button_frame, text="Start Recording", width=18, command=self.toggle_recording
        )

        tk.Button(button_frame, text="Save last 30s of video", width=18, command=self.save_last_video).grid(row=0, column=0, sticky="nsew")
        tk.Button(button_frame, text="Save last 30s of Audio", width=18, command=self.save_last_audio).grid(row=0, column=1, sticky="nsew")
        self.record_button.grid(row=0, column=2, sticky="nsew")
        self.stream_toggle_button.grid(row=1, column=0, sticky="nsew")
        tk.Button(button_frame, text="Audio filter toggle", width=18).grid(row=1, column=1, sticky="nsew")
        tk.Button(button_frame, text="Bounding Box Toggle", width=18).grid(row=1, column=2, sticky="nsew")
        
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



    '''
    Functions
    
    '''

    def name_output_file(self, str):
        bits = str.split(".")
        return f"{bits[0]}_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H-%M-%S')}.{bits[1]}"
        
    def play_audio_stream(self):
        media = self.instance.media_new(globals.audio_url)
        self.player.set_media(media)
        self.player.audio_set_volume(self.volume_slider.get())  # apply slider setting
        self.player.play()


    def stop_audio_stream(self):
        self.player.stop()


    def set_volume(self, value):
        self.player.audio_set_volume(int(value))


    # def record_audio_clip(self):
    #     def _record():
    #         output_file = self.name_output_file(self.AUDIO_OUTPUT_FILE)
    #         if os.path.exists(output_file):
    #             os.remove(output_file)
    #         options = f":sout=#file{{dst={output_file}}}"
    #         media = self.instance.media_new(globals.audio_url, options)
    #         recorder = self.instance.media_player_new()
    #         recorder.set_media(media)
    #         recorder.play()
    #         time.sleep(5)
    #         recorder.stop()
    #         print(f"Saved 5s clip to {output_file}")

    #     threading.Thread(target=_record, daemon=True).start()


    def save_last_video(self):
        output_file = self.name_output_file("media/video_clip.mp4")
        if not self.frame_buffer:
            print("No frames in buffer!")
            return 0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_file, fourcc, self.fps,
                              (self.frame_buffer[0].shape[1], self.frame_buffer[0].shape[0]))
        for f in list(self.frame_buffer):
            out.write(f)
        out.release()
        print(f"Saved last 30 seconds of video to {output_file}")
        return 1
    
    
    # Live Recording Functions
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            self.recording = True
            self.record_start_time = time.time()
            self.recorded_frames.clear()

            # Start background thread to record video + audio
            self.record_thread = threading.Thread(target=self.record_loop, daemon=True)
            self.record_thread.start()

            self.record_button.config(bg="red", text="Stop Recording")
            print("Recording started")
        else:
            # Stop recording
            self.recording = False
            self.record_button.config(bg="white", text="Start Recording")
            print("Recording stopped")


    def record_loop(self):
        """
        Background loop to capture video frames and audio while recording.
        Stops automatically after self.max_record_seconds.
        """
        # Optional: Record audio via VLC stream
        # output_file = self.name_output_file(self.recorded_audio_file)
        # options = f":sout=#file{{dst={output_file}}}"
        # media = self.instance.media_new(globals.audio_url, options)
        # recorder = self.instance.media_player_new()
        # recorder.set_media(media)
        # recorder.play()

        while self.recording:
            if self.frame_buffer:
                self.recorded_frames.append(self.frame_buffer[-1].copy())
            if time.time() - self.record_start_time >= self.max_record_seconds:
                self.recording = False
                break
            time.sleep(1 / self.fps)  # sync to frame rate

        # recorder.stop()
        self.save_video_recording()


    def save_video_recording(self):
        if not self.recorded_frames:
            print("No frames recorded!")
            return
        
        output_file = self.name_output_file(self.recorded_video_file)

        # Save video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        height, width = self.recorded_frames[0].shape[:2]
        out = cv2.VideoWriter(output_file, fourcc, self.fps, (width, height))
        for f in self.recorded_frames:
            out.write(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        out.release()
        # print(f"Video saved to {output_file}")

        # Audio is already saved by VLC to self.recorded_audio_file
        # print(f"Audio saved to {self.recorded_audio_file}")

    # Save last 30 seconds of audio functions
    def _audio_capture_loop(self):
        """
        Continuously capture audio into a rolling memory buffer.
        """
        def callback(indata, frames, time, status):
            if status:
                print(status)
            # store a copy of the chunk in the rolling buffer
            self.audio_buffer.append(indata.copy())

        with sd.InputStream(
            samplerate=self.audio_sample_rate,
            channels=self.audio_channels,
            blocksize=1024,  # chunk size
            callback=callback
        ):
            while True:
                sd.sleep(1000)  # keep stream alive


    def save_last_audio(self):
        """
        Save the last N seconds of audio from the buffer to a WAV file.
        """
        if not self.audio_buffer:
            print("No audio in buffer!")
            return

        # Concatenate all buffered chunks
        data = np.concatenate(list(self.audio_buffer), axis=0)

        # Convert float32 (-1.0 to 1.0) to 16-bit PCM
        pcm_data = (data * 32767).astype(np.int16)

        write_file = self.name_output_file(self.last_audio_clip_file)

        # Write to WAV file
        with wave.open(write_file, "wb") as wf:
            wf.setnchannels(self.audio_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.audio_sample_rate)
            wf.writeframes(pcm_data.tobytes())

        print(f"Saved last {self.audio_buffer_seconds} seconds of audio to {write_file}")