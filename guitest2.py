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
from queue import SimpleQueue, Empty

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

        global i

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
        for F in (ConnectionSetup, DeviceControl, Captures):
            frame = F(container)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        # Start controller loop in background
        # self.controller.start_loop(hz=30)

        # Show the DeviceControl screen first
        self.show_frame(DeviceControl)
        # i = i+1
        # print(f"display {i}")

    # Optional status line (doesn't have to be visible)
        self._status_var = tk.StringVar(value="UI ready")
        status = tk.Label(self, textvariable=self._status_var, anchor="w")
        status.pack(fill="x", side="bottom")

        # Start non-blocking GUI responsiveness monitor
        self._start_gui_monitor(interval_ms=50)  # adjust to 16–100 ms as you like

    def _start_gui_monitor(self, interval_ms=50):
        self._hb_q = SimpleQueue()
        self._hb_interval = interval_ms / 1000.0
        self._hb_stop = False

        # --- Tk heartbeat (runs on Tk thread): minimal work, just queue a timestamp
        def _heartbeat():
            if self._hb_stop:
                return
            try:
                self._hb_q.put_nowait(time.perf_counter())
            except Exception:
                pass
            # re-schedule next beat; no computation here
            self.after(int(self._hb_interval * 1000), _heartbeat)

        # --- Worker: computes drift/body stats off the Tk thread
        def _worker():
            last = None
            body_times = deque(maxlen=200)
            drift_times = deque(maxlen=200)
            report_every = 50
            n = 0

            while not self._hb_stop:
                try:
                    t = self._hb_q.get(timeout=1.0)
                except Empty:
                    continue

                if last is not None:
                    # how late vs expected cadence
                    drift = (t - last) - self._hb_interval
                    drift_ms = max(drift, 0.0) * 1000.0
                    drift_times.append(drift_ms)

                # Very light “body” timing: measure how fast Tk can schedule the next idle op.
                # Post a no-op back to Tk and time how long until it runs.
                start = time.perf_counter()
                finished = [False]

                def _noop():
                    finished[0] = True

                # Schedule ASAP (0 ms). This does not block here.
                self.after(0, _noop)

                # Wait a short, bounded time for it to run; this is off the Tk thread.
                # DO NOT busy-wait too hard.
                deadline = start + 0.2  # 200ms cap
                while not finished[0] and time.perf_counter() < deadline:
                    time.sleep(0.001)
                body_ms = (time.perf_counter() - start) * 1000.0
                body_times.append(body_ms)

                n += 1
                if n % report_every == 0:
                    # compute simple stats
                    def p95(xs):
                        if not xs: return 0.0
                        s = sorted(xs); return s[int(0.95 * (len(s) - 1))]
                    avg_drift = sum(drift_times) / len(drift_times) if drift_times else 0.0
                    avg_body = sum(body_times) / len(body_times) if body_times else 0.0
                    msg = (f"loop drift avg={avg_drift:.1f} ms p95={p95(drift_times):.1f} | "
                           f"dispatch (after 0) avg={avg_body:.1f} ms p95={p95(body_times):.1f}")
                    # Print from worker (not Tk). If you want it on-screen, post via after:
                    print("[GUI]", msg)
                    self.after(0, lambda m=msg: self._status_var.set(m))

                last = t

        # Start both
        self.after(int(self._hb_interval * 1000), _heartbeat)
        threading.Thread(target=_worker, daemon=True).start()

    def destroy(self):
        # Clean shutdown
        self._hb_stop = True
        super().destroy()

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
    # add.state("zoomed")  # fullscreen for Windows
    #app.attributes("-fullscreen", True)  # fullscreen for Linux
    app.mainloop()
