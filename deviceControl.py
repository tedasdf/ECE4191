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
import requests


class DeviceControl(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        ## Filenames
        self.recorded_audio_file = f"media/recorded_audio.ogg"
        self.buffer_audio_clip_file = f"media/buffer_audio.wav" # filename for the audio clip saved by the audio buffer
        self.recorded_video_file = f"media/recorded_video.mp4" # filename for the manually recorded video clip

        ## Video stream stuff
        self.fps = 24   # FPS of the stream
        self.buffer_seconds = 30  # how many seconds to keep for save past clip functionality
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)    # where frames for the past clip are stored

        ## Audio Stream stuff
        # audio buffer 
        self.audio_buffer_seconds = 30  # how many seconds of audio to keep
        self.audio_sample_rate = 44100  
        self.audio_channels = 2
        self.audio_buffer = deque(maxlen=self.audio_buffer_seconds * self.audio_sample_rate // 1024)  # 1024-frame chunks
        
        self.audio_stream_process = None
        
        # Start the audio capture in a background thread
        threading.Thread(target=self._audio_capture_loop, daemon=True).start()

        # variable for servo control
        self.focus_set()
        self.bind("<Left>", self.left_key)
        self.bind("<Right>", self.right_key)
        self.bind("<Up>", self.up_key)
        self.bind("<Down>", self.down_key)

        # variables to control the live recording function
        self.recording = False
        self.record_start_time = None
        self.max_record_seconds = 60
        self.recorded_frames = deque(maxlen=self.fps * self.max_record_seconds)
        self.record_thread = None

        self.layout()


    def layout(self):

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

        # tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        # ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1, sticky="ew")

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
            command=lambda: self.stream_toggle())
        
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


    def _name_output_file(self, str):
        """
        This is a helper function for adding the date and time that a sample was taken to the name of the file it is saved in
        """
        bits = str.split(".")
        return f"{bits[0]}_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H-%M-%S')}.{bits[1]}"


    def set_volume(self, value):
        """
        Called when the volume slider is moved, this sets the volume of the audio stream
        """
        self.player.audio_set_volume(int(value))


    ### audio stream control functions
    def play_audio_stream(self):
        """
        Initiaites the audio stream in the GUI, sourced from the audio url set in globals.py
        """
        media = self.instance.media_new(globals.audio_url)
        self.player.set_media(media)
        self.player.audio_set_volume(self.volume_slider.get())  # apply slider setting
        self.player.play()


    def stop_audio_stream(self):
        """
        Stops the audio stream that is playing
        """
        self.player.stop()

    ### Video capture rolling buffer 
    def save_last_video(self):
        output_file = self._name_output_file("media/video_clip.mp4")
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
    
    
    ### Live Recording Functions
    def toggle_recording(self):
        """
        Toggles the recording function. This is to be called by the recording button whne the user presses it
        """
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
            self.record_button.config(bg="white", text="Start Recording") # set record button back to white
            print("Recording stopped")
            # self._save_recording()


    def _record_loop(self):
        """
        Background loop to capture video frames and audio while recording.
        Stops automatically after self.max_record_seconds.
        """
        # Optional: Record audio via VLC stream
        output_file = self._name_output_file(self.recorded_audio_file)
        options = f":sout=#file{{dst={output_file}}}"
        media = self.instance.media_new(globals.audio_url, options)
        recorder = self.instance.media_player_new()
        recorder.set_media(media)
        recorder.play()

        while self.recording:
            if self.frame_buffer:
                self.recorded_frames.append(self.frame_buffer[-1].copy())
            if time.time() - self.record_start_time >= self.max_record_seconds:
                self.recording = False
                self.toggle_recording()
                print("recording limit reached")
                break
            time.sleep(1 / self.fps)  # sync to frame rate

        recorder.stop()
        self._save_video_recording()


    def _save_video_recording(self):
        """
        This function saves the manual recording to the output file.
        """
        if not self.recorded_frames:
            print("No frames recorded!")
            return
        
        output_file = self._name_output_file(self.recorded_video_file)

        # Save video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        height, width = self.recorded_frames[0].shape[:2]
        out = cv2.VideoWriter(output_file, fourcc, self.fps, (width, height))
        for f in self.recorded_frames:
            out.write(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        out.release()


    ### Audio capture rolling buffer
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

        write_file = self._name_output_file(self.buffer_audio_clip_file)

        # Write to WAV file
        with wave.open(write_file, "wb") as wf:
            wf.setnchannels(self.audio_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.audio_sample_rate)
            wf.writeframes(pcm_data.tobytes())

        print(f"Saved last {self.audio_buffer_seconds} seconds of audio to {write_file}")

    def stream_toggle(self):
        def video_loop():
            ret, frame = globals.capture.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                #frame = cv2.resize(frame, (600, 400))  # fit the label size
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
                self.video_label.after(15, video_loop)  # schedule next frame
                self.frame_buffer.append(frame.copy()) # add recording to video buffer
            # else:
            #     if globals.streaming:
            #         globals.streaming = False
            #         self.stream_toggle_button.config(text="Start Stream")
            #         self.video_label.config(image=self.stream_standby_photo)
            #         # audio_stream.stop_stream()
            #         # audio_stream.close()
            #         # p.termiate()
            #         messagebox.showerror("Error", "Video Disconnected")
            #         return

        # def audio_loop():
        #     audio_data = self.audio_stream_process.stdout.read(4096)
            
        #     if audio_data:
        #         audio_stream.write(audio_data)
        #         self.after(15, audio_loop)
        #     else:
        #         if globals.streaming:
        #             globals.streaming = False
        #             self.stream_toggle_button.config(text="Start Stream")
        #             self.video_label.config(image=self.stream_standby_photo)
        #             globals.capture.release()
        #             messagebox.showerror("Error", "Audio Disconnected")
        #             return




        if not globals.streaming:
            # Start video stream if not streaming
            globals.capture = cv2.VideoCapture(globals.video_url)
            globals.streaming = True
            self.play_audio_stream()
            self.stream_toggle_button.config(text="Stop Stream")
            video_loop()

            # Now start audio
            # self.audio_stream_process = subprocess.Popen(
            #     ["ffmpeg", "-i", globals.audio_url, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", "-"],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.DEVNULL            
            # )

            # p = pyaudio.PyAudio()
            # audio_stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)
            # threading.Thread(target=audio_loop, daemon=True).start()

        else:
            # Stop video and audio stream if already streaming
            globals.streaming = False
            globals.capture.release()
            self.stop_audio_stream()
            # audio_stream.stop_stream()
            # audio_stream.close()
            # p.termiate()

            self.stream_toggle_button.config(text="Start Stream")
            self.video_label.config(image=self.stream_standby_photo)

    def stop_video_stream(self):
        globals.capture.release()

    def move_servo(self, new_pan_angle, new_tilt_angle):
        try:
            globals.pan_angle = max(0, min(180, new_pan_angle))  # clamp between 0°–180°
            globals.tilt_angle = max(0, min(90, new_tilt_angle)) # clamp between 0°–90°
            requests.get(f"http://{globals.PI_IP}:5000/servo", params={"pan_angle": globals.pan_angle, "tilt_angle": globals.tilt_angle})
            print(f"Moved to {globals.pan_angle}° pan and {globals.tilt_angle}° tilt")  # optional feedback
        except:
            messagebox.showerror("Error", "No response from motor")

    def left_key(self, event):
        self.move_servo(globals.pan_angle + 10, globals.tilt_angle)  # increase angle
        print("left")

    def right_key(self, event):
        self.move_servo(globals.pan_angle - 10, globals.tilt_angle)  # decrease angle
        print("right")

    def up_key(self, event):
        self.move_servo(globals.pan_angle, globals.tilt_angle + 10)  # increase angle
        print("up")

    def down_key(self, event):
        self.move_servo(globals.pan_angle, globals.tilt_angle - 10)  # decrease angle
        print("down")