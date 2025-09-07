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
import pyaudio
import threading

# ------------Capture screen------------

VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".mov"]
AUDIO_EXTS = [".mp3", ".wav", ".flac", ".aac", ".ogg"]
IMAGE_EXTS = [".jpg", ".jpeg", ".png"]
ALL_EXTS = VIDEO_EXTS + AUDIO_EXTS + IMAGE_EXTS

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


# def stream_toggle(app):

#     def video_loop():
#         ret, frame = globals.capture.read()
#         if ret:
#             frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             #frame = cv2.resize(frame, (600, 400))  # fit the label size
#             img = Image.fromarray(frame)
#             imgtk = ImageTk.PhotoImage(image=img)
#             app.video_label.imgtk = imgtk
#             app.video_label.config(image=imgtk)
#             app.video_label.after(1, video_loop)  # schedule next frame
#             app.frame_buffer.append(frame.copy()) # add recording to video buffer
#         else:
#             if globals.streaming:
#                 messagebox.showerror("Error", "Video Disconnected")
#                 globals.streaming = False
#                 app.stream_toggle_button.config(text="Start Stream")
#                 app.video_label.config(image=app.stream_standby_photo)
#                 return

#     def audio_loop():
#         audio_data = globals.audio_stream_process.stdout.read(4096)
#         if audio_data:
#             globals.audio_stream.write(audio_data)
#         else:
#             if globals.streaming:
#                 messagebox.showerror("Error", "Audio Disconnected")
#                 globals.streaming = False
#                 app.stream_toggle_button.config(text="Start Stream")
#                 app.video_label.config(image=app.stream_standby_photo)
#                 return
        

#     if not globals.streaming:
#         # Start video stream if not streaming
#         globals.capture = cv2.VideoCapture(globals.video_url)
#         globals.streaming = True
#         # app.play_audio_stream()
#         app.stream_toggle_button.config(text="Stop Stream")
#         video_loop()
#         audio_loop()

#         # Now start audio
#         globals.audio_stream_process = subprocess.Popen(
#             ["ffmpeg", "-i", globals.audio_url, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", "-"],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.DEVNULL            
#         )

#         p = pyaudio.Pyaudio()
#         globals.audio_stream = p.open(format=pyaudio.paInt16, channels=2, rate=44100, output=True)
#         threading.Thread(target=audio_loop, daemon=True).start()

#     else:
#         # Stop video and audio stream if already streaming
#         globals.streaming = False
#         globals.capture.release()
#         # app.stop_audio_stream()
#         globals.audio_stream.stop_stream()
#         globals.audio_stream.close()
#         p.termiate()

#         app.stream_toggle_button.config(text="Start Stream")
#         app.video_label.config(image=app.stream_standby_photo)




# ------------Connections Screen------------

def set_link(app):
    globals.video_url = app.video_url_text.get()
    globals.audio_url = app.audio_url_text.get()
    app.title.config(text=f"Stream link updated at {datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
