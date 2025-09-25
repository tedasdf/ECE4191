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
import logging

import sounddevice as sd
import numpy as np
import wave

from deviceControl import DeviceControl
from captures import Captures
from connectionSetup import ConnectionSetup
from headless_controller import HeadlessController

# logging.basicConfig(level=logging.INFO)

class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
        self.configure(bg="lightgray")
        self.resizable(False, False)

         # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        connectionsetup_button = tk.Button(
            top_frame, text="Connection Setup",
            command=lambda: self.show_frame(ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        devicecontrol_button = tk.Button(
            top_frame, text="Device Control",
            command=lambda: self.show_frame(DeviceControl))
        devicecontrol_button.pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Captures",
            command=lambda: self.show_frame(Captures))
        captures_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)



        # Container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}  # store references to frames

        # Initialize all screens
        for F in (DeviceControl, ConnectionSetup, Captures):
            frame = F(container)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        # Start controller loop in background
        # self.controller.start_loop(hz=30)

        # Show the DeviceControl screen first
        self.show_frame(DeviceControl)

    def show_frame(self, screen):
        frame = self.frames[screen] 
        frame.tkraise()  # bring the frame to the top 


    def send_command(self, cmd):
        self.controller.send_command(cmd.encode())

    def quit_app(self):
        self.controller.stop_loop()
        self.controller.cleanup()
        self.destroy()


if __name__ == "__main__":
    # controller = HeadlessController(mqtt_broker_host_ip=globals.controller_IP.split(":")[0], mqtt_port=int(globals.controller_IP.split(":")[1]))
    # controller = None
    app = WildlifeBotApp()
    app.mainloop()