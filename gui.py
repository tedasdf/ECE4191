import tkinter as tk
from tkinter import ttk

class WildlifeBotApp(tk.Tk):
    def init(self):
        super().init()
        self.title("Wildlife Bot")
        self.geometry("1000x600")
        self.configure(bg="lightgray")

        # --- Top Menu Bar ---
        top_frame = tk.Frame(self, bg="white", pady=5)
        top_frame.pack(fill="x")

        logo = tk.Label(top_frame, text="", font=("Arial", 18))
        logo.pack(side="left", padx=10)

        tk.Button(top_frame, text="Connection setup").pack(side="left", padx=5)
        tk.Button(top_frame, text="Device Control").pack(side="left", padx=5)
        tk.Button(top_frame, text="Captures").pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # --- Main Content Area ---
        main_frame = tk.Frame(self, bg="lightgray")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Image Placeholder
        image_frame = tk.LabelFrame(main_frame, text="Camera View", width=600, height=400)
        image_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        image_placeholder = tk.Label(image_frame, text="[Camera Feed Placeholder]", bg="white")
        image_placeholder.pack(expand=True, fill="both")

        # Right: Creature Detection
        detect_frame = tk.LabelFrame(main_frame, text="Creatures Detected", width=250)
        detect_frame.pack(side="right", fill="y", padx=10, pady=10)

        creatures = ["Platypus", "Lizard", "Crocodile", "Dove"]
        for c in creatures:
            tk.Label(detect_frame, text=f"{c} - 0 samples").pack(anchor="w", padx=10, pady=2)

        tk.Button(detect_frame, text="View Recordings").pack(pady=5)
        tk.Button(detect_frame, text="Save last 30s vid").pack(pady=5)
        tk.Button(detect_frame, text="Save last 30s audio").pack(pady=5)
        tk.Button(detect_frame, text="Start/End Recording").pack(pady=5)

        tk.Button(detect_frame, text="Night Vision Toggle").pack(pady=5)
        tk.Button(detect_frame, text="Filter Audio Toggle").pack(pady=5)
        tk.Button(detect_frame, text="Bounding Box Toggle").pack(pady=5)

        # --- Bottom Section ---
        bottom_frame = tk.Frame(self, bg="lightgray")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        # Audio waveform placeholder
        waveform = tk.Label(bottom_frame, text="[Audio Waveform Placeholder]", bg="white", height=4)
        waveform.pack(fill="x", pady=5)

        # Controls (Camera + Audio)
        controls_frame = tk.Frame(bottom_frame, bg="lightgray")
        controls_frame.pack(fill="x")

        # Camera Controls
        cam_frame = tk.LabelFrame(controls_frame, text="Camera Controls")
        cam_frame.pack(side="left", padx=10)

        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(camframe, from=50, to=200, orient="horizontal").grid(row=0, column=1)

        tk.Label(cam_frame, text="Yaw:").grid(row=1, column=0, sticky="w")
        ttk.Scale(camframe, from=-90, to=90, orient="horizontal").grid(row=1, column=1)

        tk.Label(cam_frame, text="Pitch:").grid(row=2, column=0, sticky="w")
        ttk.Scale(camframe, from=-90, to=90, orient="horizontal").grid(row=2, column=1)

        # Audio Controls
        audio_frame = tk.LabelFrame(controls_frame, text="Audio Controls")
        audio_frame.pack(side="right", padx=10)

        tk.Label(audio_frame, text="Volume:").grid(row=0, column=0, sticky="w")
        ttk.Scale(audioframe, from=0, to=100, orient="horizontal").grid(row=0, column=1)

if name == "main":
    app = WildlifeBotApp()
    app.mainloop()