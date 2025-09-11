import tkinter as tk
from tkinter import ttk
from functions import *
import globals



class ConnectionSetup(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # # --- Top Menu Bar ---
        # top_frame = tk.Frame(self, bg="white", pady=5)
        # top_frame.pack(fill="x")

        # logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        # logo.pack(side="left", padx=10)

        # tk.Button(top_frame, text="Connection Setup", relief="sunken").pack(side="left", padx=5)

        # captures_button = tk.Button(
        #     top_frame, text="Device Control",
        #     command=lambda: controller.show_frame(DeviceControl))
        # captures_button.pack(side="left", padx=5)

        # connectionsetup_button = tk.Button(
        #     top_frame, text="Captures",
        #     command=lambda: controller.show_frame(Captures))
        # connectionsetup_button.pack(side="left", padx=5)

        # tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # frame for URL connections
        connection_main_frame = tk.Frame(self)
        connection_main_frame.pack(fill="both", expand=True)

        info_frame = tk.LabelFrame(connection_main_frame, text="Connection Information")
        info_frame.pack(side="top", padx=10, pady=10, fill="both")
        

        # video url section
        tk.Label(info_frame, text="Video stream URL:").pack(padx=10)
        self.video_url_text = tk.Entry(info_frame)
        self.video_url_text.pack(fill="x", padx=10, pady=10)
        self.video_url_text.insert(0, globals.video_url)

        # audio url section
        tk.Label(info_frame, text="Audio stream URL:").pack(padx=10)
        self.audio_url_text = tk.Entry(info_frame)
        self.audio_url_text.pack(fill="x", padx=10, pady=10)
        self.audio_url_text.insert(0, globals.audio_url)

        # pi url section
        tk.Label(info_frame, text="Motor control URL:").pack(padx=10)
        self.motor_url_text = tk.Entry(info_frame)
        self.motor_url_text.pack(fill="x", padx=10, pady=10)
        self.motor_url_text.insert(0, globals.PI_IP)

        self.title = tk.Label(connection_main_frame, text="")
        self.title.pack(side="top")

        connect_button = tk.Button(
            connection_main_frame, text="Connect to Stream", command=lambda: set_link(self))
        connect_button.pack(side="top", pady=100)