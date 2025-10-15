"""
High Accuracy Animal Audio Classifier - CRNN Model Integration
Integrates the trained CRNN model for real-time audio classification in the GUI
"""

# import os
# import sys
# import numpy as np
# import librosa
# import tensorflow as tf
# from tensorflow import keras
# import json
# from collections import deque
# import warnings
# warnings.filterwarnings('ignore')

# # Import config from same directory
# import config


class HighAccuracyAnimalClassifier:
    """
    High-accuracy animal audio classifier using trained CRNN model.
    Designed to work with streaming audio from the GUI.
    """
    
    def __init__(self, audio_dir=None):
        """
        Initialize the classifier
        
        Args:
            audio_dir: Not used - kept for compatibility with old interface
        """
        print("\n" + "="*60)
        print("🎵 INITIALIZING CRNN AUDIO CLASSIFIER FOR GUI")
        print("="*60)
        
        # Model paths
        self.model_path = os.path.join(config.MODEL_SAVE_DIR, config.MODEL_NAME)
        self.label_mapping_path = os.path.join(config.MODEL_SAVE_DIR, 'label_mapping.json')
        
        # Load model
        print(f"\n📥 Loading CRNN model from: {self.model_path}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model not found at {self.model_path}\n"
                "Please train the model first by running: python train_model.py"
            )
        
        self.model = keras.models.load_model(self.model_path)
        print("   ✅ Model loaded successfully!")
        
        # Load label mapping
        print(f"\n📥 Loading label mapping from: {self.label_mapping_path}")
        if not os.path.exists(self.label_mapping_path):
            raise FileNotFoundError(f"Label mapping not found at {self.label_mapping_path}")
        
        with open(self.label_mapping_path, 'r') as f:
            label_mapping = json.load(f)
        
        self.label_mapping = {int(k): v for k, v in label_mapping.items()}
        self.num_classes = len(self.label_mapping)
        self.class_names = [self.label_mapping[i] for i in range(self.num_classes)]
        
        print(f"   ✅ Loaded {self.num_classes} classes:")
        for idx, label in enumerate(self.class_names[:5]):  # Show first 5
            print(f"      {idx}: {label}")
        if self.num_classes > 5:
            print(f"      ... and {self.num_classes - 5} more")
        
        # Voting system for robust predictions
        self.prediction_history = deque(maxlen=config.VOTING_WINDOW_SIZE)
        self.confidence_history = deque(maxlen=config.VOTING_WINDOW_SIZE)
        
        # Audio processing settings
        self.sample_rate = config.SAMPLE_RATE
        self.segment_duration = config.SEGMENT_DURATION
        self.segment_samples = int(self.sample_rate * self.segment_duration)
        
        print(f"\n⚙️  Configuration:")
        print(f"   Sample Rate: {self.sample_rate} Hz")
        print(f"   Segment Duration: {self.segment_duration}s")
        print(f"   Voting Window: {config.VOTING_WINDOW_SIZE} predictions")
        print(f"   Confidence Threshold: {config.CONFIDENCE_THRESHOLD * 100}%")
        print(f"   Voting Threshold: {config.VOTING_THRESHOLD * 100}%")
        
        print("\n" + "="*60)
        print("✅ CLASSIFIER READY FOR REAL-TIME INFERENCE")
        print("="*60 + "\n")
    
    def extract_melspectrogram(self, audio):
        """
        Extract Mel-Spectrogram from audio
        
        Args:
            audio: Audio signal (numpy array)
            
        Returns:
            Mel-spectrogram in dB scale
        """
        mel_spec = librosa.feature.melspectrogram(
            y=audio,
            sr=self.sample_rate,
            n_mels=config.N_MELS,
            n_fft=config.N_FFT,
            hop_length=config.HOP_LENGTH,
            fmin=config.FMIN,
            fmax=config.FMAX
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        return mel_spec_db
    
    def preprocess_audio(self, audio, target_sr=None):
        """
        Preprocess audio for model input
        
        Args:
            audio: Raw audio signal (numpy array)
            target_sr: Target sample rate (if different from input)
            
        Returns:
            Preprocessed mel-spectrogram ready for model
        """
        # Handle different input types
        if isinstance(audio, bytes):
            audio = np.frombuffer(audio, dtype=np.int16)
        
        # Convert to float and normalize to [-1, 1]
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        
        # Ensure it's 1D
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        else:
            audio = audio.flatten()
        
        # Normalize audio
        if len(audio) > 0 and np.max(np.abs(audio)) > 0:
            audio = audio / (np.max(np.abs(audio)) + 1e-6)
        
        # Resample if needed (GUI audio is 44100 Hz, model expects 22050 Hz)
        if target_sr is not None and target_sr != self.sample_rate:
            audio = librosa.resample(audio, orig_sr=target_sr, target_sr=self.sample_rate)
        
        # Ensure correct length
        if len(audio) < self.segment_samples:
            # Pad if too short
            audio = np.pad(audio, (0, self.segment_samples - len(audio)), mode='constant')
        elif len(audio) > self.segment_samples:
            # Take the most recent segment
            audio = audio[-self.segment_samples:]
        
        # Extract Mel-Spectrogram
        mel_spec = self.extract_melspectrogram(audio)
        
        # Add batch and channel dimensions (batch, height, width, channels)
        mel_spec = mel_spec[np.newaxis, ..., np.newaxis]
        
        return mel_spec
    
    def predict_animal(self, audio_data, source_sample_rate=44100):
        """
        Predict animal from audio data
        
        Args:
            audio_data: Raw audio data (numpy array or bytes)
            source_sample_rate: Sample rate of the input audio (default: 44100 from GUI)
            
        Returns:
            List of tuples (animal_name, confidence) sorted by confidence
        """
        try:
            # Preprocess audio
            mel_spec = self.preprocess_audio(audio_data, target_sr=source_sample_rate)
            
            # Make prediction
            predictions = self.model.predict(mel_spec, verbose=0)[0]
            
            # Get all predictions sorted by confidence
            sorted_indices = np.argsort(predictions)[::-1]  # Descending order
            results = []
            
            for idx in sorted_indices:
                animal_name = self.class_names[idx]
                confidence = float(predictions[idx])
                results.append((animal_name, confidence))
            
            # Update voting history (only if confidence above threshold)
            top_prediction = results[0]
            if top_prediction[1] >= config.CONFIDENCE_THRESHOLD:
                self.prediction_history.append(top_prediction[0])
                self.confidence_history.append(top_prediction[1])
            
            return results
            
        except Exception as e:
            print(f"Error in predict_animal: {e}")
            import traceback
            traceback.print_exc()
            return [("Error", 0.0)]
    
    def get_voting_result(self):
        """
        Apply voting system to recent predictions
        
        Returns:
            Tuple of (final_prediction, vote_percentage, avg_confidence) or (None, 0, 0)
        """
        if len(self.prediction_history) == 0:
            return None, 0.0, 0.0
        
        from collections import Counter
        
        # Count votes
        vote_counts = Counter(self.prediction_history)
        most_common = vote_counts.most_common(1)[0]
        winning_class = most_common[0]
        vote_count = most_common[1]
        
        # Calculate vote percentage
        vote_percentage = vote_count / len(self.prediction_history)
        
        # Calculate average confidence for winning class
        confidences = [conf for pred, conf in zip(self.prediction_history, self.confidence_history) 
                      if pred == winning_class]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        return winning_class, vote_percentage, avg_confidence
    
    def predict_with_voting(self, audio_data, source_sample_rate=44100):
        """
        Predict with voting system for more robust results
        
        Args:
            audio_data: Raw audio data
            source_sample_rate: Sample rate of input audio
            
        Returns:
            Dictionary with current prediction and voting result
        """
        # Get current prediction
        current_predictions = self.predict_animal(audio_data, source_sample_rate)
        
        # Get voting result
        final_prediction, vote_pct, avg_conf = self.get_voting_result()
        
        return {
            'current': current_predictions,
            'voting': {
                'prediction': final_prediction,
                'vote_percentage': vote_pct,
                'avg_confidence': avg_conf,
                'is_confident': vote_pct >= config.VOTING_THRESHOLD
            }
        }
    
    def reset_voting_history(self):
        """Clear the voting history"""
        self.prediction_history.clear()
        self.confidence_history.clear()
    
    def get_info(self):
        """Get classifier information"""
        return {
            'model_path': self.model_path,
            'num_classes': self.num_classes,
            'classes': self.class_names,
            'sample_rate': self.sample_rate,
            'segment_duration': self.segment_duration,
            'voting_window_size': config.VOTING_WINDOW_SIZE,
            'confidence_threshold': config.CONFIDENCE_THRESHOLD,
            'voting_threshold': config.VOTING_THRESHOLD
        }


# Test function
if __name__ == "__main__":
    print("Testing High Accuracy Animal Classifier...")
    
    try:
        classifier = HighAccuracyAnimalClassifier()
        
        print("\n✅ Classifier initialized successfully!")
        print("\nClassifier Info:")
        info = classifier.get_info()
        for key, value in info.items():
            if key != 'classes':
                print(f"  {key}: {value}")
        
        # Test with dummy audio
        print("\n🧪 Testing with dummy audio data...")
        dummy_audio = np.random.randn(44100 * 3)  # 3 seconds of random noise
        results = classifier.predict_animal(dummy_audio, source_sample_rate=44100)
        
        print("\nTop 5 Predictions:")
        for i, (animal, conf) in enumerate(results[:5], 1):
            print(f"  {i}. {animal:20s} {conf*100:5.1f}%")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
