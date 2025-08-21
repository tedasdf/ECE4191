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

        # ---Video---
        top_frame = tk.Frame(self)
        top_frame.pack(side="top", padx=10, pady=10)

        # Left: Image Placeholder
        video_frame = tk.LabelFrame(top_frame, text="Camera View", width=600, height=400)
        video_frame.pack_propagate(False)
        video_frame.pack(side="left", padx=10, pady=10)
        #image_placeholder = tk.Label(image_frame, text="[Camera Feed Placeholder]", bg="white")
        #image_placeholder.pack(expand=True, fill="both")

        # Right
        right_frame = tk.Frame(top_frame)
        right_frame.pack(side="right", fill="both")

        # detect frame
        detect_frame = tk.LabelFrame(right_frame, text="Creatures Detected")
        detect_frame.pack(side="top", fill="y", padx=10, pady=10)

        creatures = ["Platypus", "Lizard", "Crocodile", "Dove"]
        for c in creatures:
            tk.Label(detect_frame, text=f"{c} - 0 samples").pack(anchor="w", padx=10)

        # Camera Controls
        cam_frame = tk.LabelFrame(right_frame, text="Camera Controls")
        cam_frame.pack(side="bottom", padx=10, pady=10)

        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1)

        tk.Label(cam_frame, text="Yaw:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1)

        tk.Label(cam_frame, text="Pitch:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=2, column=1)

        # button frame
        button_frame = tk.Frame(right_frame, width=250)
        button_frame.pack(side="top", fill="y")
        
        tk.Button(button_frame, text="Save last 30s", width=18).pack(pady=2)
        tk.Button(button_frame, text="Start/End Recording", width=18).pack(pady=2)
        tk.Button(button_frame, text="Night Vision Toggle", width=18).pack(pady=2)
        tk.Button(button_frame, text="Bounding Box Toggle", width=18).pack(pady=2)

        # ---Audio---
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side="bottom", padx=10, pady=10)

        # Left
        bottom_left_frame = tk.Frame(bottom_frame)
        bottom_left_frame.pack(side="left", fill="both")

        audio_frame = tk.LabelFrame(bottom_left_frame, text="Audio Visualisation", width=600, height="150")
        audio_frame.pack_propagate(False)
        audio_frame.pack(side="top", padx=10, pady=10, fill="y")
        #image_placeholder = tk.Label(image_frame, text="[Camera Feed Placeholder]", bg="white")
        #image_placeholder.pack(expand=True, fill="both")
        
        # button frame
        bottom_button_frame = tk.Frame(bottom_left_frame, width=250)
        bottom_button_frame.pack(side="top", fill="y")
        
        tk.Button(bottom_button_frame, text="Save last 30s", width=18).pack(side="left", padx=2)
        tk.Button(bottom_button_frame, text="Start/End Recording", width=18).pack(side="left", padx=2)
        tk.Button(bottom_button_frame, text="Night Vision Toggle", width=18).pack(side="left", padx=2)
        tk.Button(bottom_button_frame, text="Bounding Box Toggle", width=18).pack(side="left", padx=2)

        # Right
        bottom_right_frame = tk.Frame(bottom_frame)
        bottom_right_frame.pack(side="right", fill="both")

        # detect frame
        bottom_detect_frame = tk.LabelFrame(bottom_right_frame, text="Creatures Detected")
        bottom_detect_frame.pack(side="top", fill="y", padx=10, pady=10)

        for c in creatures:
            tk.Label(bottom_detect_frame, text=f"{c} - 0 samples").pack(anchor="w", padx=10)


        # Audio Controls
        volumn_frame = tk.LabelFrame(bottom_right_frame, text="Audio Controls")
        volumn_frame.pack(side="bottom", padx=10, pady=10)

        tk.Label(volumn_frame, text="Vol:").grid(row=0, column=0, sticky="w")
        ttk.Scale(volumn_frame, from_=0, to=100, orient="horizontal").grid(row=0, column=1)

        tk.Label(volumn_frame, text="Gain:").grid(row=1, column=0, sticky="w")
        ttk.Scale(volumn_frame, from_=0, to=100, orient="horizontal").grid(row=1, column=1)



        


        

        

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
