import tkinter as tk
from tkinter import ttk

class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
        ##self.geometry("1600x800")
        self.configure(bg="lightgray")
        self.resizable(False,False)

        # Container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}  # store references to frames

        # Initialize all screens
        for F in (DeviceControl, ConnectionSetup, Captures):
            frame = F(container, self)
            self.frames[F] = frame
            frame.config(width=1600, height=800, bd=3, relief="ridge")
            #frame.pack_propagate(False)
            frame.grid(row=0, column=0, sticky="nsew")

        # Show the home screen first
        self.show_frame(DeviceControl)

    def show_frame(self, screen):
        frame = self.frames[screen]
        frame.tkraise()  # bring the frame to the top

class DeviceControl(tk.Frame):
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

        tk.Button(top_frame, text="Device Control", relief="sunken").pack(side="left", padx=5)

        captures_button = tk.Button(top_frame, text="Captures",
                           command=lambda: controller.show_frame(Captures))
        captures_button.pack(side="left", padx=5)

        tk.Label(top_frame, text="Wildlife Bot", font=("Arial", 18, "bold"), bg="white").pack(side="right", padx=15)

        # --- Main Content Area ---
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: Image Placeholder
        image_frame = tk.LabelFrame(main_frame, text="Camera View", width=600, height=400)
        image_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        #image_placeholder = tk.Label(image_frame, text="[Camera Feed Placeholder]", bg="white")
        #image_placeholder.pack(expand=True, fill="both")

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

        # Toggle buttons
        tk.Button(detect_frame, text="Night Vision Toggle").pack(pady=5)
        tk.Button(detect_frame, text="Filter Audio Toggle").pack(pady=5)
        tk.Button(detect_frame, text="Bounding Box Toggle").pack(pady=5)

        # --- Bottom Section ---
        bottom_frame = tk.LabelFrame(self, text="Audio Visualisation")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        # Audio waveform placeholder
        waveform = tk.Label(bottom_frame, text="[Audio Waveform Placeholder]", bg="white", height=4)
        waveform.pack(fill="x", pady=5)

        # Controls (Camera + Audio)
        controls_frame = tk.Frame(bottom_frame)
        controls_frame.pack(fill="x")

        # Camera Controls
        cam_frame = tk.LabelFrame(controls_frame, text="Camera Controls")
        cam_frame.pack(side="left", padx=10)

        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1)

        tk.Label(cam_frame, text="Yaw:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1)

        tk.Label(cam_frame, text="Pitch:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=2, column=1)

        # Audio Controls
        audio_frame = tk.LabelFrame(controls_frame, text="Audio Controls")
        audio_frame.pack(side="right", padx=10)

        tk.Label(audio_frame, text="Volume:").grid(row=0, column=0, sticky="w")
        ttk.Scale(audio_frame, from_=0, to=100, orient="horizontal").grid(row=0, column=1)


# Capture screen
class Captures(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        label = tk.Label(self, text="This is the Captures Screen", font=("Arial", 16))
        label.pack(pady=20)

        button = tk.Button(self, text="Back to Home",
                           command=lambda: controller.show_frame(DeviceControl))
        button.pack()

# Connection Setup Screen
class ConnectionSetup(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        label = tk.Label(self, text="This is the Connection Setup Screen", font=("Arial", 16))
        label.pack(pady=20)

        button = tk.Button(self, text="Back to Home",
                           command=lambda: controller.show_frame(DeviceControl))
        button.pack()

if __name__ == "__main__":
    app = WildlifeBotApp()
    app.mainloop()
