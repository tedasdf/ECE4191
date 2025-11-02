import time
from collections import deque
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
i = 0

class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
        self.configure(bg="lightgray")
        self.resizable(False, False)

        # --- ADD: simple metrics store
        self._metrics = {
            "loop_drift_ms": 0.0,
            "loop_body_ms": 0.0,
            "last_nav_ms": 0.0,
        }

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="🐨", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        # wrap show_frame calls so we time them
        connectionsetup_button = tk.Button(
            top_frame, text="Connection Setup",
            command=lambda: self._timed_nav(self.show_frame, "ConnectionSetup", ConnectionSetup))
        connectionsetup_button.pack(side="left", padx=5)

        devicecontrol_button = tk.Button(
            top_frame, text="Device Control",
            command=lambda: self._timed_nav(self.show_frame, "DeviceControl", DeviceControl))
        devicecontrol_button.pack(side="left", padx=5)

        captures_button = tk.Button(
            top_frame, text="Captures",
            command=lambda: self._timed_nav(self.show_frame, "Captures", Captures))
        captures_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # Container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (ConnectionSetup, DeviceControl, Captures):
            frame = F(container)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # --- ADD: status bar to surface metrics (optional but handy)
        status_frame = tk.Frame(self, bg="#f4f4f4")
        status_frame.pack(fill="x")
        self._status_var = tk.StringVar(value="UI ready")
        tk.Label(status_frame, textvariable=self._status_var, anchor="w").pack(fill="x", padx=8, pady=2)

        # --- ADD: start event-loop monitor
        self._start_loop_monitor(interval_ms=100)

        # show default screen
        self.show_frame(DeviceControl)

    # unchanged
    def show_frame(self, screen):
        frame = self.frames[screen]
        frame.tkraise()

    # --- ADD: wrap navigation to time it
    def _timed_nav(self, fn, name, *args, **kwargs):
        t0 = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            self._metrics["last_nav_ms"] = dt_ms
            print(f"[NAV] {name} took {dt_ms:.2f} ms")
            self._update_status_line()

    # --- ADD: monitor event-loop responsiveness
    def _start_loop_monitor(self, interval_ms=100):
        self._loop_last = time.perf_counter()
        self._loop_interval = interval_ms / 1000.0
        self._loop_bodies = deque(maxlen=200)
        self._loop_drifts = deque(maxlen=200)

        def tick():
            t_now = time.perf_counter()
            # lateness vs expected cadence
            drift_ms = (t_now - self._loop_last - self._loop_interval) * 1000.0

            # measure how long it takes to flush pending UI work right now
            b0 = time.perf_counter()
            # Do not call long/blocking code here; just a quick flush is fine:
            self.update_idletasks()
            body_ms = (time.perf_counter() - b0) * 1000.0

            self._loop_last = t_now
            self._metrics["loop_drift_ms"] = max(drift_ms, 0.0)
            self._metrics["loop_body_ms"] = body_ms
            self._loop_bodies.append(body_ms)
            self._loop_drifts.append(drift_ms)

            # print occasional summary
            if len(self._loop_bodies) == self._loop_bodies.maxlen:
                def p95(xs):
                    s = sorted(xs); 
                    return s[int(0.95*(len(s)-1))]
                print(f"[LOOP] body avg={sum(self._loop_bodies)/len(self._loop_bodies):.2f} ms "
                      f"p95={p95(self._loop_bodies):.2f} ms | "
                      f"drift avg={sum(self._loop_drifts)/len(self._loop_drifts):.2f} ms "
                      f"p95={p95(self._loop_drifts):.2f} ms")
                self._loop_bodies.clear(); self._loop_drifts.clear()

            self._update_status_line()
            self.after(int(self._loop_interval * 1000), tick)

        self.after(int(self._loop_interval * 1000), tick)

    # --- ADD: tiny dashboard in the status bar
    def _update_status_line(self):
        s = (f"loop drift: {self._metrics['loop_drift_ms']:.1f} ms  |  "
             f"loop body: {self._metrics['loop_body_ms']:.1f} ms  |  "
             f"last nav: {self._metrics['last_nav_ms']:.1f} ms")
        self._status_var.set(s)

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
    # add.state("zoomed")  # fullscreen for Windows
    #app.attributes("-fullscreen", True)  # fullscreen for Linux
    app.mainloop()
