"""
Configuration file for Animal Sound Classification System - GUI Integration
Centralizes all parameters for easy tuning and experimentation
"""

import os

# ========================================
# Directory Paths (relative to this file)
# ========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_SAVE_DIR = os.path.join(BASE_DIR, "models")
LOG_DIR = os.path.join(BASE_DIR, "logs", "audio")

# Create directories if they don't exist
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ========================================
# Audio Processing Parameters
# ========================================
SAMPLE_RATE = 22050  # Hz - Standard for audio processing (good balance between quality and computation)
SEGMENT_DURATION = 3.0  # seconds - Duration of each audio segment
SEGMENT_SAMPLES = int(SAMPLE_RATE * SEGMENT_DURATION)

# Mel-Spectrogram parameters
N_MELS = 128  # Number of mel bands (frequency resolution)
N_FFT = 2048  # FFT window size
HOP_LENGTH = 512  # Number of samples between successive frames
FMIN = 20  # Minimum frequency (Hz)
FMAX = 8000  # Maximum frequency (Hz) - covers most animal vocalizations

# ========================================
# Real-Time Inference Parameters
# ========================================
# Voting system for robust predictions
VOTING_WINDOW_SIZE = 3  # Number of recent predictions to consider (10 predictions = 30 seconds)
CONFIDENCE_THRESHOLD = 0.65  # Minimum confidence to accept a prediction
VOTING_THRESHOLD = 0.65  # Minimum percentage of votes needed to declare detection (70% = 7/10)

# GUI Integration
GUI_AUDIO_SAMPLE_RATE = 44100  # Hz - GUI streams at 44100 Hz
CLASSIFICATION_INTERVAL = 3.0  # seconds - How often to run classification

# ========================================
# Label Processing
# ========================================
# Background noise label
BACKGROUND_LABEL = "Background"

# Model files
MODEL_NAME = "animal_classifier_best.h5"
LABEL_MAPPING_FILE = "label_mapping.json"

# Extract animal name from filename (e.g., "BatA.wav" -> "Bat")
def extract_label_from_filename(filename):
    """
    Extract the animal name from a filename.
    Removes trailing letters (A, B, etc.) and file extension.
    
    Args:
        filename: e.g., "BatA.wav", "KookaburraB.wav"
    
    Returns:
        Animal name: e.g., "Bat", "Kookaburra"
    """
    # Remove extension
    name = os.path.splitext(filename)[0]
    
    # Remove trailing single letters (A, B, etc.)
    if len(name) > 1 and name[-1].isalpha() and name[-2].isalpha():
        # Check if last part is a single capital letter
        if name[-1].isupper():
            return name[:-1]
    
    return name

# ========================================
# Print Configuration Summary
# ========================================
def print_config():
    """Print a summary of the current configuration"""
    print("=" * 60)
    print("ANIMAL SOUND CLASSIFICATION - GUI CONFIGURATION")
    print("=" * 60)
    print(f"\n📁 Directories:")
    print(f"   Models: {MODEL_SAVE_DIR}")
    print(f"   Logs: {LOG_DIR}")
    
    print(f"\n🎵 Audio Processing:")
    print(f"   Model Sample Rate: {SAMPLE_RATE} Hz")
    print(f"   GUI Sample Rate: {GUI_AUDIO_SAMPLE_RATE} Hz")
    print(f"   Segment Duration: {SEGMENT_DURATION}s")
    print(f"   Mel Bands: {N_MELS}")
    print(f"   FFT Size: {N_FFT}")
    
    print(f"\n🎯 Inference:")
    print(f"   Classification Interval: {CLASSIFICATION_INTERVAL}s")
    print(f"   Voting Window: {VOTING_WINDOW_SIZE} predictions ({VOTING_WINDOW_SIZE * CLASSIFICATION_INTERVAL}s)")
    print(f"   Confidence Threshold: {CONFIDENCE_THRESHOLD * 100}%")
    print(f"   Voting Threshold: {VOTING_THRESHOLD * 100}%")
    print(f"   Detection Requires: {int(VOTING_WINDOW_SIZE * VOTING_THRESHOLD)} out of {VOTING_WINDOW_SIZE} predictions")
    
    print("=" * 60)
    print()

if __name__ == "__main__":
    print_config()
