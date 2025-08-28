import os
import tkinter as tk
from tkinter import ttk
from functions import *
from PIL import Image, ImageTk
import cv2
import globals

class WildlifeBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wildlife Bot")
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
            frame.config(width=1600, height=800)
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
        self.video_frame = tk.LabelFrame(top_frame, text="Camera View", width=600, height=400)
        self.video_frame.pack_propagate(False)
        self.video_frame.pack(side="left", padx=10, pady=10)

        # stream_label = tk.Label(video_frame, bd=1, relief="groove")
        # stream_label.pack(padx=10, pady=10)
        # url="https://www3.cde.ca.gov/download/rod/big_buck_bunny.mp4"
        # stream_video(url, stream_label)


        self.video_label = tk.Label(self.video_frame, bd=1, relief="groove")
        self.video_label.pack(expand=True, fill="both")
        self.video_label.pack(padx=10, pady=10)

        # OpenCV stream
        url_bigpi = "udp://10.175.112.23:5000"
        #self.cap = cv2.VideoCapture(globals.url)

        #self.update_video()
        #stream_vid(self)



        # Right
        right_frame = tk.Frame(top_frame)
        right_frame.pack(side="right", fill="both")

        # detect frame
        detect_frame = tk.LabelFrame(right_frame, text="Creatures Detected")
        detect_frame.pack(side="top", fill="y", padx=10, pady=10)

        detect_scrollbar = tk.Scrollbar(detect_frame)
        detect_scrollbar.pack(side="right", fill="y")

        detect_listbox = tk.Listbox(detect_frame, yscrollcommand=detect_scrollbar.set, height=6)
        detect_listbox.pack(side="left", fill="none", expand=False)

        detect_scrollbar.config(command=detect_listbox.yview)

        creatures = ["Platypus", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove"]
        for i in creatures:
            detect_listbox.insert("end", f"{i}")

        # Camera Controls
        cam_frame = tk.LabelFrame(right_frame, text="Camera Controls")
        cam_frame.pack(side="bottom", padx=10, pady=10, fill="x")

        tk.Label(cam_frame, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=50, to=200, orient="horizontal").grid(row=0, column=1)

        tk.Label(cam_frame, text="Pan:").grid(row=1, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=-90, to=90, orient="horizontal").grid(row=1, column=1)

        tk.Label(cam_frame, text="Tilt:").grid(row=2, column=0, sticky="w")
        ttk.Scale(cam_frame, from_=0, to=90, orient="horizontal").grid(row=2, column=1)

        # button frame
        button_frame = tk.Frame(right_frame, width=250)
        button_frame.pack(side="top", fill="y")
        
        tk.Button(button_frame, text="Save last 30s", width=18).pack(pady=2)
        tk.Button(button_frame, text="Start/End Recording", width=18).pack(pady=2)
        tk.Button(button_frame, text="Night Vision Toggle", width=18).pack(pady=2)
        tk.Button(button_frame, text="Bounding Box Toggle", width=18).pack(pady=2)
        tk.Button(button_frame, text="Start Stream", width=18, bg="white", command=lambda: stream_vid(self)).pack(pady=2)

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

        bottom_detect_scrollbar = tk.Scrollbar(bottom_detect_frame)
        bottom_detect_scrollbar.pack(side="right", fill="y")

        bottom_detect_listbox = tk.Listbox(bottom_detect_frame, yscrollcommand=bottom_detect_scrollbar.set, height=6)
        bottom_detect_listbox.pack(side="left", fill="none", expand=False)

        bottom_detect_scrollbar.config(command=bottom_detect_listbox.yview)

        creatures = ["Platypus", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove", "Lizard", "Crocodile", "Dove"]
        for i in creatures:
            bottom_detect_listbox.insert("end", f"{i}")


        # Audio Controls
        volumn_frame = tk.LabelFrame(bottom_right_frame, text="Audio Controls")
        volumn_frame.pack(side="bottom", padx=10, pady=10, fill="x")

        tk.Label(volumn_frame, text="Vol:").grid(row=0, column=0, sticky="w")
        ttk.Scale(volumn_frame, from_=0, to=100, orient="horizontal").grid(row=0, column=1)

        tk.Label(volumn_frame, text="Gain:").grid(row=1, column=0, sticky="w")
        ttk.Scale(volumn_frame, from_=0, to=100, orient="horizontal").grid(row=1, column=1)

'''
    def update_video(self):
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (600, 400))  # fit the label size
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            self.after(30, self.update_video)  # schedule next frame
'''



# Capture screen
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

        self.url_text = tk.Entry(info_frame, width=70)
        self.url_text.pack()
        #self.url_text.insert(0,"http://192.168.77.1:7123/stream.mjpg")
        self.url_text.insert(0,"https://www3.cde.ca.gov/download/rod/big_buck_bunny.mp4")
        

        self.title = tk.Label(connection_main_frame, text="")
        self.title.pack(side="top")

        connect_button = tk.Button(connection_main_frame, text="Connect to Stream", command=lambda: set_link(self))
        connect_button.pack(side="top", pady=100)



if __name__ == "__main__":
    app = WildlifeBotApp()
    app.mainloop()