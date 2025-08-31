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
import os
from collections import deque

class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
        self.configure(bg="lightgray")
        # self.resizable(False,False)
        self.resizable(True, True)

        # Container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}  # store references to frames

        # Initialize all screens
        for F in (DeviceControl, ConnectionSetup, Captures):
            frame = F(container, self)
            self.frames[F] = frame
            frame.config(width=1600, height=700)
            frame.grid(row=0, column=0, sticky="nsew")

        # Show the DeviceControl screen first
        self.show_frame(DeviceControl)

    def show_frame(self, screen):
        frame = self.frames[screen]
        frame.tkraise()  # bring the frame to the top


class DeviceControl(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.fps = 25
        self.buffer_seconds = 5
        self.frame_buffer = deque(maxlen=self.fps * self.buffer_seconds)

        # Configure grid for the whole screen
        self.grid_rowconfigure(0, weight=0)   # menu bar row (fixed height)
        self.grid_rowconfigure(1, weight=4)   # video + controls
        self.grid_rowconfigure(2, weight=2)   # audio section
        self.grid_columnconfigure(0, weight=1)

        # --- Top Menu Bar ---
        menu = tk.Frame(self, bg="white", pady=5)
        menu.grid(row=0, column=0, sticky="ew")

        logo = tk.Label(menu, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        tk.Button(menu, text="Connection Setup",
                  command=lambda: controller.show_frame(ConnectionSetup)).pack(side="left", padx=5)
        tk.Button(menu, text="Device Control", relief="sunken").pack(side="left", padx=5)
        tk.Button(menu, text="Captures",
                  command=lambda: controller.show_frame(Captures)).pack(side="left", padx=5)
        tk.Label(menu, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # --- Middle (Video + Controls) ---
        middle = tk.Frame(self)
        middle.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        middle.grid_columnconfigure(0, weight=3)   # video area bigger
        middle.grid_columnconfigure(1, weight=1)   # side controls smaller
        middle.grid_rowconfigure(0, weight=1)

        # Left video
        self.video_frame = tk.LabelFrame(middle, text="Camera View")
        self.video_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.video_frame.grid_propagate(True)

        self.video_label = tk.Label(self.video_frame, bd=1, relief="groove")
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)
        img = Image.open("stream_standby_image.jpg").resize((600, 400))
        self.stream_standby_photo = ImageTk.PhotoImage(img)
        self.video_label.config(image=self.stream_standby_photo)

        # Right panel (detections + controls)
        right = tk.Frame(middle)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right.grid_rowconfigure(0, weight=2)
        right.grid_rowconfigure(1, weight=1)
        right.grid_rowconfigure(2, weight=1)

        detect_frame = tk.LabelFrame(right, text="Creatures Detected")
        detect_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        detect_frame.grid_rowconfigure(0, weight=1)
        detect_frame.grid_columnconfigure(0, weight=1)

        detect_scrollbar = tk.Scrollbar(detect_frame)
        detect_scrollbar.pack(side="right", fill="y")
        detect_listbox = tk.Listbox(detect_frame, yscrollcommand=detect_scrollbar.set)
        detect_listbox.pack(side="left", fill="both", expand=True)
        detect_scrollbar.config(command=detect_listbox.yview)
        for i in ["Platypus", "Lizard", "Crocodile", "Dove"] * 4:
            detect_listbox.insert("end", i)

        cam_frame = tk.LabelFrame(right, text="Camera Controls")
        cam_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1, sticky="ew")
        tk.Label(cam_frame, text="Pan:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1, sticky="ew")
        tk.Label(cam_frame, text="Tilt:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=0, to=90, orient="horizontal").grid(row=2, column=1, sticky="ew")

        button_frame = tk.Frame(right)
        button_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        tk.Button(button_frame, text="Save last 30s", width=18, command=self.save_last_clip).pack(pady=2)
        tk.Button(button_frame, text="Start/End Recording", width=18).pack(pady=2)
        tk.Button(button_frame, text="Night Vision Toggle", width=18).pack(pady=2)
        tk.Button(button_frame, text="Bounding Box Toggle", width=18).pack(pady=2)
        self.stream_toggle_button = tk.Button(button_frame, text="Start Stream", width=18,
                                              command=lambda: stream_toggle(self))
        self.stream_toggle_button.pack(pady=2)

        # --- Bottom (Audio Section) ---
        bottom = tk.Frame(self)
        bottom.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=1)

        audio_frame = tk.LabelFrame(bottom, text="Audio Visualisation")
        audio_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        controls = tk.Frame(bottom)
        controls.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        tk.Button(controls, text="Save 5s", command=self.record_audio_clip, width=12).pack(pady=2)
        tk.Button(controls, text="Play Stream", command=self.play_audio_stream, width=12).pack(pady=2)
        tk.Button(controls, text="Stop Stream", command=self.stop_audio_stream, width=12).pack(pady=2)
        self.volume_slider = tk.Scale(controls, from_=0, to=100, orient="horizontal",
                                      label="Volume", command=self.set_volume, length=200)
        self.volume_slider.pack(pady=2)
        self.volume_slider.set(50)

        # VLC
        self.is_playing = False
        self.AUDIO_OUTPUT_FILE = "media/audio_clip.ogg"
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()


    def play_audio_stream(self):
        if not self.is_playing:
            media = self.instance.media_new(globals.audio_url)
            self.player.set_media(media)
            self.player.audio_set_volume(self.volume_slider.get())  # apply slider setting
            self.player.play()
            self.is_playing = True

    def stop_audio_stream(self):
        if self.is_playing:
            self.player.stop()
            self.is_playing = False

    def set_volume(self, value):
        """Update VLC player volume when slider changes."""
        self.player.audio_set_volume(int(value))

    def record_audio_clip(self):
        """Save 5 seconds of audio to AUDIO_OUTPUT_FILE."""
        def _record():
            # Delete old file if exists
            if os.path.exists(self.AUDIO_OUTPUT_FILE):
                os.remove(self.AUDIO_OUTPUT_FILE)

            # Tell VLC to save stream
            options = f":sout=#file{{dst={self.AUDIO_OUTPUT_FILE}}}"
            media = self.instance.media_new(self.STREAM_URL, options)
            recorder = self.instance.media_player_new()
            recorder.set_media(media)

            recorder.play()
            time.sleep(5)  # Record for 5 seconds
            recorder.stop()

            print(f"Saved 5s clip to {self.AUDIO_OUTPUT_FILE}")

        threading.Thread(target=_record, daemon=True).start()

    def save_last_clip(self):
        if not self.frame_buffer:
            print("No frames in buffer!")
            return

        # Define output file
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter("media/video_clip.mp4", fourcc, self.fps,
                            (self.frame_buffer[0].shape[1], self.frame_buffer[0].shape[0]))

        for f in list(self.frame_buffer):
            out.write(f)
        out.release()
        print("Saved last 5 seconds of video to video_clip.mp4")



# Captures screen
class Captures(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        connectionsetup_button = tk.Button(top_frame, text="Connection Setup",
                           command=lambda: controller.show_frame(ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        captures_button = tk.Button(top_frame, text="Device Control",
                           command=lambda: controller.show_frame(DeviceControl))
        captures_button.pack(side="left", padx=5)

        tk.Button(top_frame, text="Captures", relief="sunken").pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True)
        
        '''
        files_listbox = tk.Listbox(main_frame, font=("Arial", 12))
        files_listbox.pack(fill="both", expand=True, padx=20, pady=20)

        show_files("./media", files_listbox)
        '''

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



# Connection Setup Screen
class ConnectionSetup(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        tk.Button(top_frame, text="Connection Setup", relief="sunken").pack(side="left", padx=5)

        captures_button = tk.Button(top_frame, text="Device Control",
                           command=lambda: controller.show_frame(DeviceControl))
        captures_button.pack(side="left", padx=5)

        connectionsetup_button = tk.Button(top_frame, text="Captures",
                           command=lambda: controller.show_frame(Captures))
        connectionsetup_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        connection_main_frame = tk.Frame(self)
        connection_main_frame.pack(fill="both", expand=True)
        
        info_frame = tk.LabelFrame(connection_main_frame, text="Connection Information")
        info_frame.pack(side="top", padx=100, pady=50, fill="both", expand=True)

        self.video_url_text = tk.Entry(info_frame, width=70)
        self.video_url_text.pack()
        self.video_url_text.insert(0, globals.video_url) #"https://www3.cde.ca.gov/download/rod/big_buck_bunny.mp4"
        

        self.title = tk.Label(connection_main_frame, text="")
        self.title.pack(side="top")

        connect_button = tk.Button(connection_main_frame, text="Connect to Stream", command=lambda: set_link(self))
        connect_button.pack(side="top", pady=100)



if __name__ == "__main__":
    app = WildlifeBotApp()
    app.mainloop()