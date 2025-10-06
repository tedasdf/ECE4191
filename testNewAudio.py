import socket
import threading
import wave
import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np

# Audio settings
UDP_IP = "0.0.0.0"
UDP_PORT = 5004
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Initialize PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK_SIZE)

# Recording setup
recording = []
is_recording = False

# AI model placeholder
def process_audio_for_ai(audio_chunk):
    # Convert bytes to numpy array
    audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
    # Feed to AI model here
    pass

# UDP listener thread
def listen_udp():
    global is_recording
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    while True:
        data, _ = sock.recvfrom(CHUNK_SIZE * 32)  # 2 bytes per sample
        stream.write(data)
        process_audio_for_ai(data)
        if is_recording:
            recording.append(data)

# Save recording to WAV
def save_recording():
    wf = wave.open("recorded_audio.wav", 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(recording))
    wf.close()

# Tkinter GUI
def start_recording():
    global is_recording, recording
    recording = []
    is_recording = True
    status_label.config(text="Recording...")

def stop_recording():
    global is_recording
    is_recording = False
    save_recording()
    status_label.config(text="Recording saved.")

app = tk.Tk()
app.title("Live UDP Audio Stream")

ttk.Button(app, text="Start Recording", command=start_recording).pack(pady=10)
ttk.Button(app, text="Stop Recording", command=stop_recording).pack(pady=10)
status_label = ttk.Label(app, text="Idle")
status_label.pack(pady=10)

# Start UDP listener
threading.Thread(target=listen_udp, daemon=True).start()

app.mainloop()
