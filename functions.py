import os
import tkinter as tk
from tkinter import filedialog, messagebox, Listbox
import datetime
import platform
import subprocess
import cv2
from PIL import Image, ImageTk
import globals
import time
import datetime

# ------------Capture screen------------

VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".mov"]
AUDIO_EXTS = [".mp3", ".wav", ".flac", ".aac"]
IMAGE_EXTS = [".jpg", ".jpeg", ".png"]
ALL_EXTS = VIDEO_EXTS + AUDIO_EXTS + IMAGE_EXTS

# function used for folder access with custom directory (Not used atm)
def browse_folder(listbox):
    folder = filedialog.askdirectory() # this pops up a screen asking for directory
    if not folder:
        return
    show_files(folder, listbox)

# used to display audio and video files (Not used atm)
def show_files(folder, listbox):
    # Clear existing list
    listbox.delete(0, tk.END)

    try:
        files = os.listdir(folder)
        # Filter for audio/video files
        media_files = [f for f in files if os.path.splitext(f)[1].lower() in ALL_EXTS]

        if not media_files:
            messagebox.showinfo("No Media", "No audio or video files found in this folder.")
            return

        for f in media_files:
            listbox.insert(tk.END, f)

    except Exception as e:
        messagebox.showerror("Error", str(e))


def populate_tree(folder, tree, fileext):
    # Clear existing treeview
    for item in tree.get_children():
        tree.delete(item)

    try:
        files = os.listdir(folder)
        # Filter for audio/video files
        media_files = [f for f in files if os.path.splitext(f)[1].lower() in fileext]

        if not media_files:
            messagebox.showinfo("No Media", "No audio or video files found in this folder.")
            return

        for f in media_files:
            filepath = os.path.join(folder, f)

            name = os.path.splitext(f)[0]
            size = os.path.getsize(filepath) / 1024 # to display it in KB
            ext = os.path.splitext(f)[1].upper()
            mtime = os.path.getmtime(filepath)
            last_modified = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

            tree.insert("", "end", text=name, values=(last_modified, f"{size:.1f} KB", ext))

    except Exception as e:
        #messagebox.showerror("Error", str(e))
        return

def tree_open_file(event, mediadir, tree):
    selection = tree.selection()

    if not selection:
        return

    item_id = selection[0]
    filename = tree.item(item_id, "text") + tree.item(item_id, "values")[2]
    filepath = os.path.join(mediadir, filename)

    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", filepath])
        else:  # Linux / Unix
            subprocess.call(["xdg-open", filepath])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{e}")    



# ------------Video streaming------------

# def stream_video(url, label):
#     # Open the video stream
#     capture = cv2.VideoCapture(url)

#     def update_frame():
#         ret, frame = capture.read()
#         if ret:
#             # Convert BGR (OpenCV) → RGB (Pillow)
#             frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            
#             # Update the label
#             label.imgtk = img
#             label.configure(image=img)

#         # Call update again after 15 ms
#         label.after(15, update_frame)

#     update_frame()


def stream_toggle(app):

    def update_frame():
        ret, frame = globals.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            #frame = cv2.resize(frame, (600, 400))  # fit the label size
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            app.video_label.imgtk = imgtk
            app.video_label.config(image=imgtk)
            app.video_label.after(25, update_frame)  # schedule next frame
            app.frame_buffer.append(frame.copy())
        # else:
        #     if globals.streaming:
        #         messagebox.showerror("Error", "Stream Disconnected")
        #         globals.streaming = False
        #         app.stream_toggle_button.config(text="Start Stream")
        #         app.video_label.config(image=app.stream_standby_photo)
        #         return

        

    if not globals.streaming:
        # Start video and audio stream if not streaming
        globals.capture = cv2.VideoCapture(globals.video_url)
        globals.streaming = True
        app.play_audio_stream()
        app.stream_toggle_button.config(text="Stop Stream")
        update_frame()
    else:
        # Stop video and audio stream if already streaming
        globals.streaming = False
        globals.capture.release()
        app.stop_audio_stream()
        app.stream_toggle_button.config(text="Start Stream")
        app.video_label.config(image=app.stream_standby_photo)




# ------------Connections Screen------------

def set_link(app):
    globals.video_url = app.video_url_text.get()
    globals.audio_url = app.audio_url_text.get()
    app.title.config(text=f"Stream link updated at {datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
