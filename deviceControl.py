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

from webRTCmultiporcessing import WebRTCStream
from ultralytics import YOLO

import sounddevice as sd
import numpy as np
import wave
import requests

from headless_controller import HeadlessController

import socket
import pyaudio

# Import the high accuracy audio classifier
from high_accuracy_classifier import HighAccuracyAnimalClassifier

pan_angle = 45  # start at middle
tilt_angle = 0
crane_angle = 0

class DeviceControl(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        ## Filenames
        ## make directories for media if they don't already exist
        os.makedirs("media", exist_ok=True)
        os.makedirs("media/audio_detections", exist_ok=True)
        os.makedirs("media/recordings/audio", exist_ok=True)
        os.makedirs("media/recordings/video", exist_ok=True)
        os.makedirs("media/visual_detections", exist_ok=True)


        ## Video stream stuff
        self.fps = 24   # FPS of the stream
        self.buffer_seconds = 30  # how many seconds to keep for save past clip functionality
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)    # where frames for the past clip are stored

        ## Audio Stream stuff
        # audio stream settings
        self.AUDIO_IP = "0.0.0.0"
        self.AUDIO_PORT = 5004
        self.AUDIO_CHUNK_SIZE = 1024
        self.AUDIO_FORMAT = pyaudio.paInt16
        self.AUDIO_CHANNELS = 1
        self.AUDIO_RATE = 44100

        self.volume_level = 1.0
        # audio buffer 
        self.audio_buffer_seconds = 30  # how many seconds of audio to keep
        self.audio_buffer = deque(maxlen=self.audio_buffer_seconds * self.AUDIO_RATE // (self.AUDIO_CHUNK_SIZE*4))  # 1024-frame chunks
        
        # an array to hold the audio recording data
        self.audio_recording = []

        ## Audio Classification Setup
        # Initialize the audio classifier
        self.audio_classifier = None
        self.classification_enabled = False
        self.classification_thread = None
        
        # Voting system tracking
        self.detected_animals = {}  # Track which animals have been officially detected via voting
        self.last_announced_animal = None  # Track last announced detection to avoid spam
        
        # Initialize audio classifier in a separate thread to avoid blocking UI
        threading.Thread(target=self._init_audio_classifier, daemon=True).start()


        # Cooldown tracker
        self.last_key_time = 0
        self.key_cooldown = 0.1  # 100 ms between keypress handling

        # variables to control the live recording function
        self.recording = False
        self.record_start_time = None
        self.max_record_seconds = 60
        self.recorded_frames = deque(maxlen=self.fps * self.max_record_seconds)
        self.record_thread = None

        # Variable to control the camera torches
        self.torch_1 = tk.BooleanVar(value=False)
        self.torch_2 = tk.BooleanVar(value=False)
        self.awb_enabled = tk.BooleanVar(value=False)

        ########
        self.webrtc_client = WebRTCStream("http://192.168.212.90:8889/cam")
        # stream.start_connection()

        # if stream.is_connected():
        #     print("Connected!")

        self.webrtc_loop = None
        self.webrtc_connection_future = None
        self.webrtc_close_future = None

        self.command_controller = HeadlessController(
            mqtt_broker_host_ip=globals.controller_IP.split(":")[0], 
            mqtt_port=int(globals.controller_IP.split(":")[1])
            )

        self.yolo_model: YOLO = YOLO("best.pt")  # load a pretrained YOLOv8n model
        self.toggle_model = False

        # self.webrtc_client.start_thread()
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

        # variable for servo control
        self.video_label.focus_set() # TODO what the fuck is this
        self.video_label.bind("<KeyPress>", self.keydown)
        self.video_label.bind("<KeyRelease>", self.keyup)
        self.video_label.bind("<Button-1>", lambda e: self.video_label.focus_set())

        # Right panel
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # detect frame
        detect_frame = tk.LabelFrame(right_frame, text="Creatures Detected")
        detect_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        detect_scrollbar = tk.Scrollbar(detect_frame)
        detect_scrollbar.pack(side="right", fill="y")

        self.detect_listbox = tk.Listbox(detect_frame, yscrollcommand=detect_scrollbar.set)
        self.detect_listbox.pack(side="left", fill="both", expand=True)

        detect_scrollbar.config(command=self.detect_listbox.yview)

        detect_scrollbar.config(command=self.detect_listbox.yview)
        # detect_scrollbar.config(command=self.detect_listbox.yview)

        # Add initial message while audio classifier loads
        self.detect_listbox.insert("end", "Audio classifier loading...")
        self.detect_listbox.insert("end", "Please wait...")
        
        # Audio classification toggle button
        audio_controls_frame = tk.Frame(detect_frame)
        audio_controls_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        self.audio_classification_button = tk.Button(
            audio_controls_frame, 
            text="Start Audio Detection", 
            command=self.toggle_audio_classification,
            state=tk.DISABLED  # Disabled until classifier loads
        )
        self.audio_classification_button.pack(side="left", padx=5)
        # Add initial message while audio classifier loads
        self.detect_listbox.insert("end", "Audio classifier loading...")
        self.detect_listbox.insert("end", "Please wait...")
        
        # Audio classification toggle button
        audio_controls_frame = tk.Frame(detect_frame)
        audio_controls_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        self.audio_classification_button = tk.Button(
            audio_controls_frame, 
            text="Start Audio Detection", 
            command=self.toggle_audio_classification,
            state=tk.DISABLED  # Disabled until classifier loads
        )
        self.audio_classification_button.pack(side="left", padx=5)

        # Camera Controls
        cam_frame = tk.LabelFrame(right_frame, text="Camera Controls")
        cam_frame.pack(side="bottom", padx=10, pady=10, fill="x")
        cam_frame.columnconfigure(0, weight=1)
        cam_frame.columnconfigure(1, weight=1) 
        cam_frame.columnconfigure(2, weight=1)

        # tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        # ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1, sticky="ew")

        # tk.Label(cam_frame, text="Pan:").grid(row=1, column=0, sticky="w")
        # ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1, sticky="ew")

        # tk.Label(cam_frame, text="Tilt:").grid(row=2, column=0, sticky="w")
        # ttk.Scale(cam_frame, from_=0, to=90, orient="horizontal").grid(row=2, column=1, sticky="ew")

        def torch_1_control():
            try:
                requests.get(
                    f"http://{globals.PI_IP}:5000/torch", 
                    params={
                        "torch_1": 1 if not self.torch_1.get() else 0, 
                    },
                    timeout=10
                )
                self.torch_1.set(not self.torch_1.get())
                btn_torch_1.config(text=f"Torch 1: {'ON' if self.torch_1.get() else 'OFF'}")
            except requests.Timeout:
                print("Request timed out - Torch 1.")

        def torch_2_control():
            try:
                requests.get(
                    f"http://{globals.PI_IP}:5000/torch", 
                    params={
                        "torch_2": 1 if not self.torch_2.get() else 0, 
                    },
                    timeout=10
                )
                self.torch_2.set(not self.torch_2.get())
                btn_torch_2.config(text=f"Torch 2: {'ON' if self.torch_2.get() else 'OFF'}")
            except requests.Timeout:
                print("Request timed out - Torch 2.")

        def awb_control():
            self.awb_enabled.set(not self.awb_enabled.get())
            btn_awb.config(text=f"AWB: {'ON' if self.awb_enabled.get() else 'OFF'}")

        btn_torch_1 = tk.Button(
            cam_frame, 
            text=f"Torch 1: {'ON' if self.torch_1.get() else 'OFF'}", 
            command=torch_1_control
        )
        btn_torch_1.grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        btn_torch_2 = tk.Button(
            cam_frame, 
            text=f"Torch 1: {'ON' if self.torch_2.get() else 'OFF'}", 
            command=torch_2_control
        )
        btn_torch_2.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        btn_awb = tk.Button(
            cam_frame,
            text=f"AWB: {'ON' if self.awb_enabled.get() else 'OFF'}",
            command=awb_control
        )
        btn_awb.grid(row=3, column=2, sticky="ew", padx=5, pady=5)

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
        # tk.Button(button_frame, text="Audio filter toggle", width=18).grid(row=1, column=1, sticky="nsew")

        self.controller_button = tk.Button(
            button_frame,
            text="Start Controls",
            width=18,
            command=lambda: self.command_controller.start_loop()
        )
        self.controller_button.grid(row=1, column=1, sticky="nsew")

        def toggle_yolo():
            self.toggle_model = not self.toggle_model
            btn_yolo.config(text=f"YOLO Model: {'ON' if self.toggle_model else 'OFF'}")

        btn_yolo = tk.Button(button_frame, text="Bounding Box Toggle", width=18, command=toggle_yolo)
        btn_yolo.grid(row=1, column=2, sticky="nsew")

        # Volume slider
        self.volume_slider = tk.Scale(
            right_frame, from_=0, to=100, orient="horizontal",
            label="Volume", command=self.set_volume, length=200
        )
        self.volume_slider.pack(pady=2, fill="x", expand=True)
        self.volume_slider.set(50)  # default volume
        
        # --- Audio Section ---
        # bottom_frame = tk.Frame(self)
        # bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Left: Audio Visualization
        # bottom_left_frame = tk.Frame(bottom_frame)
        # bottom_left_frame.pack(side="left", fill="both", expand=True)

        # audio_frame = tk.LabelFrame(bottom_left_frame, text="Audio Visualisation")
        # audio_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        # Right: Audio controls
        # bottom_right_frame = tk.Frame(bottom_frame)
        # bottom_right_frame.pack(side="right", fill="both")

        # audio_controls_frame = tk.Frame(bottom_right_frame)
        # audio_controls_frame.pack(side="top", fill="x", padx=10, pady=5)

        # self.volume_slider = tk.Scale(
        #     audio_controls_frame, from_=0, to=100, orient="horizontal",
        #     label="Volume", command=self.set_volume, length=200
        # )
        # self.volume_slider.pack(pady=2, fill="x", expand=True)
        # self.volume_slider.set(50)  # default volume

        # VLC player instance
        # self.instance = vlc.Instance("--quiet --network-caching=0")
        # self.player = self.instance.media_player_new()


    def _name_output_file(self, str):
        """
        This is a helper function for adding the date and time that a sample was taken to the name of the file it is saved in
        """
        return str + datetime.datetime.now().isoformat(sep="_", timespec='seconds').replace(":", "-")
        # bits = str.split(".")
        # return f"{bits[0]}_{datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H-%M-%S')}.{bits[1]}"


    def set_volume(self, value):
        """
        Called when the volume slider is moved, this sets the volume of the audio stream
        """
        self.volume_level = int(value)*2/100 # normalise down to between 0 and 2


    ### audio stream control functions
    # def play_audio_stream(self):
    #     """
    #     Initiaites the audio stream in the GUI, sourced from the audio url set in globals.py
    #     """
    #     print("audio stream started")
    #     media = self.instance.media_new(globals.audio_url)
    #     self.player.set_media(media)
    #     self.player.audio_set_volume(self.volume_slider.get())  # apply slider setting
    #     self.player.play()


    # def stop_audio_stream(self):
    #     """
    #     Stops the audio stream that is playing
    #     """
    #     self.player.stop()

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
    

    def capture_photo(self, animal_name):
        if not self.frame_buffer:
            print("No frames in buffer!")
            return 0

        # Get the most recent frame (last element in the buffer)
        last_frame = self.frame_buffer[-1]

        # Create the output directory if it doesn't exist
        output_dir = os.path.join("media", "visual_detections", animal_name)
        os.makedirs(output_dir, exist_ok=True)

        # Build the filename
        filename = self._name_output_file(animal_name + "_") + ".jpg"
        write_path = os.path.join(output_dir, filename)

        # Save the frame as a JPEG
        success = cv2.imwrite(write_path, last_frame)

        if success:
            print(f"Saved photo: {write_path}")
            return write_path
        else:
            print("Failed to save photo.")
            return 0
    
    
    ### Live Recording Functions
    def toggle_recording(self):
        """
        Toggles the recording function. This is to be called by the recording button when the user presses it
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
        # # Optional: Record audio via VLC stream
        # output_file = self._name_output_file(self.recorded_audio_file)
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
                self.toggle_recording()
                print("recording limit reached")
                break
            time.sleep(1 / self.fps)  # sync to frame rate

        # recorder.stop()
        self._save_video_recording()
        self._save_audio_recording()


    def _save_video_recording(self):
        """
        This function saves the manual recording to the output file.
        """
        if not self.recorded_frames:
            print("No frames recorded!")
            return
        
        output_file = self._name_output_file("media/recordings/video/recorded_video_") + '.mp4'

        # Save video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        height, width = self.recorded_frames[0].shape[:2]
        out = cv2.VideoWriter(output_file, fourcc, self.fps, (width, height))
        for f in self.recorded_frames:
            out.write(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        out.release()


    ### Audio capture rolling buffer
    # def _audio_capture_loop(self):
    #     """
    #     Continuously capture audio into a rolling memory buffer.
    #     """
    #     def callback(indata, frames, time, status):
    #         if status:
    #             print(status)
    #         # store a copy of the chunk in the rolling buffer
    #         self.audio_buffer.append(indata.copy())

    #     with sd.InputStream(
    #         samplerate=self.audio_sample_rate,
    #         channels=self.audio_channels,
    #         blocksize=1024,  # chunk size
    #         callback=callback
    #     ):
    #         while True:
    #             sd.sleep(1000)  # keep stream alive

    def _save_audio_recording(self):
        """
        This function saves the manual audio recording to the output file.
        """
        if not self.audio_recording:
            print("No audio recorded!")
            return
        
        output_file = self._name_output_file("media/recordings/audio/recorded_audio_") + '.wav'

        wf = wave.open(output_file, 'wb')
        wf.setnchannels(self.AUDIO_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(self.AUDIO_RATE)
        wf.writeframes(b''.join(self.audio_recording))
        wf.close()
        self.audio_recording = [] # clear the recording once its saved


    def save_last_audio(self, N = 30, folder = None, filename = None):
        """
        Save the last N seconds of audio from the buffer to a WAV file.
        """

        if N > 30 or N < 0:
            print("Invalid N, returning to default")
            N = 30
        
        if not folder:
            folder = 'recordings/audio/'

        if not filename:
            filename = 'buffer_audio'

        if not self.audio_buffer:
            print("No audio in buffer!")
            return

        # Concatenate all buffered chunks
        slice_index = int(len(self.audio_buffer) * (N/30))
        # print("buffer slices:", self.audio_buffer[:slice_index])
        data = b"".join(list(self.audio_buffer)[:slice_index])
        pcm_data = np.frombuffer(data, dtype=np.int16)

        write_file = 'media/' + folder + self._name_output_file(filename+'_') + ".wav"

        # create folder if it doesn't exist
        os.makedirs('media/' + folder, exist_ok=True)

        # Write to WAV file
        with wave.open(write_file, "wb") as wf:
            wf.setnchannels(self.AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.AUDIO_RATE)
            wf.writeframes(pcm_data.tobytes())

        print(f"Saved last {N} seconds of audio to {write_file}")


    def stream_toggle(self):

        def gray_world_awb(img):
            # Convert to float
            img_float = img.astype(np.float32)
            
            # Compute average per channel
            avg_b = np.mean(img_float[:, :, 0])
            avg_g = np.mean(img_float[:, :, 1])
            avg_r = np.mean(img_float[:, :, 2])
            
            # Compute scale factors
            avg_gray = (avg_b + avg_g + avg_r) / 3
            scale_b = avg_gray / avg_b
            scale_g = avg_gray / avg_g
            scale_r = avg_gray / avg_r
            
            # Apply scaling
            img_float[:, :, 0] *= scale_b
            img_float[:, :, 1] *= scale_g
            img_float[:, :, 2] *= scale_r
            
            # Clip and convert back
            img_float = np.clip(img_float, 0, 255).astype(np.uint8)
            return img_float

        def video_loop():
            # Get the frame from the webrtc thread
            if (not globals.streaming):
                print("Video loop: Not streaming, exiting video loop")
                return

            frame = self.webrtc_client.get_frame()
            if frame is None:
                # self.video_label.after(20, video_loop)  # schedule next frame
                print("No frame received")
                return
            
            if self.toggle_model:
                results = self.yolo_model(frame, conf=0.5)


            # Some basic image processing
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            #frame = cv2.resize(frame, (600, 400))  # fit the label size
            if self.awb_enabled.get():
                frame = gray_world_awb(frame)

            if self.toggle_model:
                annotated_frame = results[0].plot()
                frame = annotated_frame

            # Display the frame in the GUI
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

            # Schedule the next frame update
            self.video_label.after(20, video_loop)  # schedule next frame
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

        def _audio_stream_loop(sock):
            # Empty the 30 second buffer
            self.audio_buffer.clear()
            while True:
                data, _ = sock.recvfrom(self.AUDIO_CHUNK_SIZE * 32)  # 2 bytes per sample

                # add audio chunk to 30 second buffer
                self.audio_buffer.append(data)

                # If recording, add the data to the recording
                if self.recording:
                    self.audio_recording.append(data)

                # Playback with volume adjustment
                audio_bytes = np.frombuffer(data, dtype=np.int16)
                adjusted = (audio_bytes * self.volume_level).astype(np.int16)
                self.audio_stream.write(adjusted.tobytes())
                # self.audio_stream.write(data)

                if not globals.streaming:
                    return
            

        if not globals.streaming:
            # Start video stream if not streaming
            globals.streaming = True
            self.stream_toggle_button.config(text="Stop Stream")
            
            # uncomment below
            self.webrtc_client.set_stream_link(globals.video_url)
            
            # self.webrtc_client.start_thread()
            self.webrtc_client.start_connection()

            if not self.webrtc_client.is_connected():
                print("WebRTC Connection failed, restaring thread")
                globals.streaming = False
                self.stream_toggle_button.config(text="Start Stream")
                self.webrtc_client.close_thread()
                # self.webrtc_client.start_thread()
            else:
                video_loop()

            # uncomment above

            # self.webrtc_loop = asyncio.new_event_loop()
            # threading.Thread(target=lambda: self.webrtc_loop.run_forever(), daemon=True).start()
            # self.webrtc_connection_future = asyncio.run_coroutine_threadsafe(
            #     self.webrtc_client.connect_to_server(
            #         vid_label=self.video_label,
            #         frame_buffer=self.frame_buffer
            #     ),
            #     self.webrtc_loop
            # )

            # Now start audio
            # self.audio_stream_process = subprocess.Popen(
            #     ["ffmpeg", "-i", globals.audio_url, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", "-"],
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.DEVNULL            
            # )

            # create a socket and bind it to the audio stream ip and port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.AUDIO_IP, self.AUDIO_PORT))
            
            # Initialize PyAudio
            p = pyaudio.PyAudio()
            self.audio_stream = p.open(format=self.AUDIO_FORMAT, channels=self.AUDIO_CHANNELS, rate=self.AUDIO_RATE, output=True, frames_per_buffer=self.AUDIO_CHUNK_SIZE)
            threading.Thread(target=_audio_stream_loop, daemon=True, args=[sock]).start() #disable audio stream temporarily

        else:
            # Stop video and audio stream if already streaming
            globals.streaming = False
            # globals.capture.release()
            # print("Stopping WebRTC connection...")
            # self.webrtc_close_future = asyncio.run_coroutine_threadsafe(
            #     self.webrtc_client.close_connection(),
            #     self.webrtc_loop
            # )
            # print("Waiting for WebRTC connection to close...")
            # self.webrtc_close_future.result()  # wait for closure to complete
            # print("Waiting for WebRTC connection thread to finish...")
            # self.webrtc_connection_future.result()  # wait for connection to finish

            # print("WebRTC connection closed.")
            # if self.webrtc_loop:
            #     self.webrtc_loop.call_soon_threadsafe(self.webrtc_loop.stop)
            #     self.webrtc_loop = None
            # print("WebRTC event loop stopped.")

            self.webrtc_client.stop_connection()
            # self.webrtc_client.close_thread()
            print("WebRTC connection closed.")

            # self.stop_audio_stream()
            # audio_stream.stop_stream()
            # audio_stream.close()
            # p.termiate()

            self.stream_toggle_button.config(text="Start Stream")
            self.video_label.config(image=self.stream_standby_photo)

    def stop_video_stream(self):
        globals.capture.release()

    def keyup(self, e):
        stateChange = False
        if e.keysym == "Up" and globals.upKeyState:
            globals.upKeyState = False
            stateChange = True
            # send tilt stop command
            # self.sendServoControl("tiltStop")
            

        elif e.keysym == "Down" and globals.downKeyState:
            globals.downKeyState = False
            stateChange = True
            # send tilt stop command
            # self.sendServoControl("tiltStop")

        elif e.keysym == "Left" and globals.leftKeyState:
            globals.leftKeyState = False
            stateChange = True
            # send tilt stop command
            # self.sendServoControl("panStop")

        elif e.keysym == "Right" and globals.rightKeyState: # work 
            globals.rightKeyState = False
            stateChange = True
            # send tilt stop command
            # self.sendServoControl("panStop")

        elif e.keysym == "apostrophe" and globals.apostropheState: # work 
            globals.apostropheState = False
            stateChange = True
            # send tilt down command
        
        elif e.keysym == "slash" and globals.slashState: # work 
            globals.slashState = False
            stateChange = True
            # send tilt down command

        if stateChange:
            print(e.keysym, 'released')

    def keydown(self, e):
        global pan_angle
        global tilt_angle
        global crane_angle


        stateChange = False
        if e.keysym == "Up" and not globals.upKeyState:
            globals.upKeyState = True
            stateChange = True
            # send tilt up command
            # self.sendServoControl("tiltUp")
            try:
                tilt_angle = max(tilt_angle - 10, 0)
                print(f"tilt angle {tilt_angle}")
                self.command_controller.send_gimbal_command("y", tilt_angle)
            except:
                pass

        elif e.keysym == "Down" and not globals.downKeyState:
            globals.downKeyState = True
            stateChange = True
            # send tilt down command
            # self.sendServoControl("tiltDown")
            try:
                tilt_angle = min(tilt_angle + 10, 90)
                print(f"tilt angle {tilt_angle}")
                self.command_controller.send_gimbal_command("y", tilt_angle)
            except:
                pass

        elif e.keysym == "Left" and not globals.leftKeyState:
            globals.leftKeyState = True
            stateChange = True
            # send tilt down command
            # self.sendServoControl("panLeft")
            try:
                pan_angle = min(pan_angle + 5, 90)
                print(f"pan angle {pan_angle}")
                self.command_controller.send_gimbal_command("x", pan_angle)
            except:
                pass

        elif e.keysym == "Right" and not globals.rightKeyState:
            globals.rightKeyState = True
            stateChange = True
            # send tilt down command
            # self.sendServoControl("panRight")
            try:
                pan_angle = max(pan_angle - 5, 0)
                print(f"pan angle {pan_angle}")
                self.command_controller.send_gimbal_command("x", pan_angle)
            except:
                pass
        
        elif e.keysym == "apostrophe" and not globals.apostropheState:
            globals.apostropheState = True
            stateChange = True
            try:
                crane_angle = min(crane_angle + 10, 90)
                print(f"crane angle {crane_angle}")
                self.command_controller.send_gimbal_command("c", crane_angle)
            except:
                pass
        
        elif e.keysym == "slash" and not globals.slashState:
            globals.slashState = True
            stateChange = True
            try:
                crane_angle = max(crane_angle - 10, 0)
                print(f"crane angle {crane_angle}")
                self.command_controller.send_gimbal_command("c", crane_angle)
            except:
                pass
        
        if stateChange:
            print(e.keysym, 'pressed')


    ## Audio Classification Methods ##
    
    def _init_audio_classifier(self):
        """Initialize the audio classifier in a background thread"""
        try:
            print("Initializing audio classifier...")
            audio_dir = "ECE4191 - Potential Audio Targets"
            
            if not os.path.exists(audio_dir):
                print(f"Warning: Audio directory '{audio_dir}' not found!")
                self.after(0, self._update_classifier_status, "Audio files not found")
                return
            
            # Initialize the high accuracy classifier
            # Ensure logs directory exists and use it for both model and GUI logging
            self.logs_dir = os.path.join(os.getcwd(), "logs", "audio")
            os.makedirs(self.logs_dir, exist_ok=True)
            # GUI-side log file for top-1 occurrences
            self.gui_log_path = os.path.join(self.logs_dir, "gui_audio_top1.log")
            if not os.path.exists(self.gui_log_path):
                try:
                    with open(self.gui_log_path, "a") as f:
                        f.write(f"# GUI Audio Top-1 Log - started {datetime.datetime.now().isoformat()}\n")
                except Exception:
                    pass

            self.audio_classifier = HighAccuracyAnimalClassifier(audio_dir)
            self.after(0, self._update_classifier_status, "CRNN classifier ready ✅")
            print("CRNN audio classifier initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing audio classifier: {e}")
            self.after(0, self._update_classifier_status, f"Error: {str(e)}")
    
    def _update_classifier_status(self, message):
        """Update the UI with classifier status - called from main thread"""
        self.detect_listbox.delete(0, tk.END)
        self.detect_listbox.insert("end", message)
        
        if self.audio_classifier is not None:
            self.audio_classification_button.config(state=tk.NORMAL)
    
    def toggle_audio_classification(self):
        """Toggle audio classification on/off"""
        if self.audio_classifier is None:
            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "Audio classifier not ready")
            return
        
        if not self.classification_enabled:
            # Start classification
            self.classification_enabled = True
            self.audio_classification_button.config(text="Stop Audio Detection", bg="red")
            
            # Reset voting system and detection tracking
            self.detected_animals = {}
            self.last_announced_animal = None
            if self.audio_classifier:
                self.audio_classifier.reset_voting_history()
            
            # Start classification thread
            self.classification_thread = threading.Thread(target=self._classification_loop, daemon=True)
            self.classification_thread.start()
            
            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "🎵 Audio detection started!")
            self.detect_listbox.insert("end", "   Analyzing every 3 seconds...")
            self.detect_listbox.insert("end", "   Voting window: 30 seconds (10 predictions)")
            self.detect_listbox.insert("end", "   Detection requires 70% vote agreement")
            print("CRNN audio classification started (3-second intervals with voting)")
        else:
            # Stop classification
            self.classification_enabled = False
            self.audio_classification_button.config(text="Start Audio Detection", bg="SystemButtonFace")
            
            self.detect_listbox.delete(0, tk.END)
            self.detect_listbox.insert("end", "🛑 Audio detection stopped")
            
            # Show final summary if any detections
            if self.detected_animals:
                self.detect_listbox.insert("end", "")
                self.detect_listbox.insert("end", "📊 Session Summary:")
                sorted_detections = sorted(self.detected_animals.items(), key=lambda x: x[1], reverse=True)
                for animal, count in sorted_detections:
                    self.detect_listbox.insert("end", f"   {animal}: {count} confirmed detections")

            print("Audio classification stopped")
    
    def _classification_loop(self):
        """Background thread for continuous audio classification using CRNN model with voting"""
        while self.classification_enabled and self.audio_classifier is not None:
            try:
                # Get audio data from buffer
                if len(self.audio_buffer) > 0:
                    # Get recent audio from buffer (last ~3 seconds for one prediction)
                    # GUI audio is 44100 Hz, we need ~3 seconds = 132300 samples
                    samples_needed = int(3.0 * self.AUDIO_RATE)  # 3 seconds at 44100 Hz
                    
                    # Convert buffer to audio array
                    raw_audio_data = b"".join(self.audio_buffer)
                    audio_data = np.frombuffer(raw_audio_data, dtype=np.int16)
                    
                    # Take the most recent samples
                    if len(audio_data) > samples_needed:
                        audio_data = audio_data[-samples_needed:]
                    
                    # Ensure it's 1D (mono)
                    if len(audio_data.shape) > 1:
                        audio_data = np.mean(audio_data, axis=1)
                    else:
                        audio_data = audio_data.flatten()
                    
                    # Check if audio has meaningful content (not silence)
                    audio_magnitude = np.max(np.abs(audio_data))
                    
                    if audio_magnitude > 100:  # Threshold for int16 audio (adjust as needed)
                        # Get predictions from CRNN model WITH VOTING
                        # Pass source sample rate so model can resample properly
                        result = self.audio_classifier.predict_with_voting(
                            audio_data, 
                            source_sample_rate=self.AUDIO_RATE
                        )
                        
                        # Update UI from main thread
                        self.after(0, self._update_detections, result)
                    else:
                        # No meaningful audio detected
                        self.after(0, self._update_detections_silence)
                
                # Wait before next classification (3 seconds to match segment duration)
                time.sleep(3.0)  # 3-second intervals to match model training
                
            except Exception as e:
                print(f"Error in classification loop: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, self._update_detections_error, str(e))
                time.sleep(3.0)
    
    def _update_detections(self, result):
        """
        Update the creatures detected listbox with voting-based detections
        
        Args:
            result: Dictionary with 'current' predictions and 'voting' results
                {
                    'current': [(animal, confidence), ...],
                    'voting': {
                        'prediction': animal_name,
                        'vote_percentage': 0.7,
                        'avg_confidence': 0.85,
                        'is_confident': True/False
                    }
                }
        """
        if not self.classification_enabled:
            return
        
        # Extract current predictions and voting result
        current_predictions = result.get('current', [])
        voting_info = result.get('voting', {})
        
        # Get voting decision
        voted_animal = voting_info.get('prediction')
        vote_pct = voting_info.get('vote_percentage', 0.0)
        avg_conf = voting_info.get('avg_confidence', 0.0)
        is_confident = voting_info.get('is_confident', False)
        
        # Clear current list
        self.detect_listbox.delete(0, tk.END)
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.detect_listbox.insert("end", f"🕒 {timestamp} - Audio Analysis (3s):")
        self.detect_listbox.insert("end", "=" * 45)
        
        # Show top 3 current predictions (real-time, before voting)
        self.detect_listbox.insert("end", "📊 Current Prediction:")
        for i, (animal, confidence) in enumerate(current_predictions[:3], 1):
            confidence_percent = confidence * 100
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            display_text = f"{emoji} #{i}: {animal:<15} ({confidence_percent:5.1f}%)"
            self.detect_listbox.insert("end", display_text)
        
        self.detect_listbox.insert("end", "=" * 45)
        
        # Show voting status
        if voted_animal:
            self.detect_listbox.insert("end", " ️  Voting Window (30s):")
            
            # Show vote percentage as progress bar
            bar_length = 20
            filled = int(bar_length * vote_pct)
            bar = "█" * filled + "░" * (bar_length - filled)
            self.detect_listbox.insert("end", f"   {voted_animal}:")
            self.detect_listbox.insert("end", f"   [{bar}] {vote_pct*100:.0f}%")
            self.detect_listbox.insert("end", f"   Confidence: {avg_conf*100:.1f}%")
            
            # Check if this is a CONFIRMED DETECTION
            if is_confident:
                # Official detection - animal has passed voting threshold!
                self.detect_listbox.insert("end", "")
                self.detect_listbox.insert("end", "✅ ANIMAL DETECTED! ✅")
                self.detect_listbox.insert("end", f"🎯 {voted_animal}")
                self.detect_listbox.insert("end", "")
                
                # Track detection
                if voted_animal not in self.detected_animals:
                    self.detected_animals[voted_animal] = 0
                self.detected_animals[voted_animal] += 1

                if voted_animal != "Background":
                    self.save_last_audio(N = 15, folder = f"audio_detections/{voted_animal}/", filename = voted_animal)
                
                # Announce new detection (avoid spam)
                if self.last_announced_animal != voted_animal:
                    print(f"\n{'='*60}")
                    print(f"🚨 NEW ANIMAL DETECTED: {voted_animal} 🚨")
                    print(f"   Vote: {vote_pct*100:.0f}% | Confidence: {avg_conf*100:.1f}%")
                    print(f"{'='*60}\n")
                    self.last_announced_animal = voted_animal
                    
                    # Log to file
                    try:
                        if hasattr(self, 'gui_log_path') and self.gui_log_path:
                            with open(self.gui_log_path, "a") as f:
                                f.write(f"{datetime.datetime.now().isoformat()} - DETECTION: {voted_animal} (Vote: {vote_pct*100:.0f}%, Conf: {avg_conf*100:.1f}%)\n")
                    except Exception:
                        pass
            else:
                # Not enough votes yet
                from config import VOTING_THRESHOLD
                needed_pct = VOTING_THRESHOLD * 100
                self.detect_listbox.insert("end", f"   ⏳ Need {needed_pct:.0f}% to confirm")
        else:
            self.detect_listbox.insert("end", "🗳️  Voting Window: Empty")
            self.detect_listbox.insert("end", "   Waiting for predictions...")
        
        self.detect_listbox.insert("end", "=" * 45)
        
        # Show detection summary if any animals have been detected
        if self.detected_animals:
            self.detect_listbox.insert("end", "📋 Confirmed Detections:")
            sorted_detections = sorted(self.detected_animals.items(), key=lambda x: x[1], reverse=True)
            for animal, count in sorted_detections[:5]:  # Show top 5
                self.detect_listbox.insert("end", f"   ✓ {animal}: {count}x")
        
        # Auto-scroll to bottom
        self.detect_listbox.see(tk.END)
        
        # Console log (simplified)
        if is_confident:
            log_msg = f"DETECTED: {voted_animal} (Vote: {vote_pct*100:.0f}%, Conf: {avg_conf*100:.1f}%)"
        else:
            top = current_predictions[0] if current_predictions else ("None", 0.0)
            log_msg = f"Current: {top[0]} ({top[1]*100:.1f}%) | Voting: {voted_animal or 'None'} ({vote_pct*100:.0f}%)"
        print(f"Audio: {log_msg}")
    
    def _update_detections_silence(self):
        """Update listbox when no meaningful audio detected"""
        print("silence detected...")
        if not self.classification_enabled:
            return
            
        #timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        #self.detect_listbox.delete(0, tk.END)
        #self.detect_listbox.insert("end", f"🕒 {timestamp} (10s interval)")
        #self.detect_listbox.insert("end", "🔇 Low audio level...")
        #self.detect_listbox.insert("end", "Listening for animal sounds...")
    
    def _update_detections_error(self, error_msg):
        """Update listbox when classification error occurs"""
        if not self.classification_enabled:
            return
            
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.detect_listbox.delete(0, tk.END)
        self.detect_listbox.insert("end", f"🕒 {timestamp} (3s interval)")
        self.detect_listbox.insert("end", f"❌ Error: {error_msg}")
        self.detect_listbox.insert("end", "Retrying in 3 seconds...")