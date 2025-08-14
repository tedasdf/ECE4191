import cv2
import os
import time
from datetime import datetime

# === SETTINGS ===
OUTPUT_DIR = "captured_images"
CAPTURE_INTERVAL = 2  # seconds between captures
CAMERA_SOURCE = 0     # 0 for default webcam, or your camera index/URL
CAPTURE_NUM = 100  # Number of images to capture


# === SETUP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
animal_type = "cat"
# Open the video stream
cap = cv2.VideoCapture(CAMERA_SOURCE)
if not cap.isOpened():
    raise IOError("❌ Cannot open camera. Check the source or connection.")

print("📷 Continuous capture started. Press Ctrl+C to stop.")

try:
    for _ in range(CAPTURE_NUM):  # Capture 100 frames
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Frame not captured, retrying...")
            continue

        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT_DIR}/img_{animal_type}_{timestamp}.jpg"

        # Save the frame
        cv2.imwrite(filename, frame)
        print(f"Saved {filename}")

        # Wait before capturing the next frame
        time.sleep(CAPTURE_INTERVAL)

except KeyboardInterrupt:
    print("\nCapture stopped by user.")

finally:
    cap.release()
    print(" Camera released.")
