#!/usr/bin/env python3
"""
Simplified Real-time Audio Classification System for Australian Animals
Designed for maximum accuracy on specific target recordings
"""

import numpy as np
import librosa
import sounddevice as sd
import os
import pickle
import logging
from datetime import datetime
from typing import List, Tuple, Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import threading
import time
import warnings
warnings.filterwarnings('ignore')

class SimpleAudioFeatureExtractor:
    """Extract robust audio features for classification"""
    
    def __init__(self, sr=22050, n_mfcc=13):
        self.sr = sr
        self.n_mfcc = n_mfcc
    
    def extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """Extract robust feature vector from audio"""
        try:
            # Ensure audio is 1D and has minimum length
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            min_length = 2048
            if len(audio_data) < min_length:
                audio_data = np.pad(audio_data, (0, min_length - len(audio_data)), mode='constant')
            
            # Normalize audio
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            else:
                return np.zeros(50)  # Return zeros for silent audio
            
            features = []
            
            # MFCC features - most important for animal sounds
            try:
                mfccs = librosa.feature.mfcc(y=audio_data, sr=self.sr, n_mfcc=self.n_mfcc)
                # Statistical features from MFCCs
                features.extend(np.mean(mfccs, axis=1))  # 13 features
                features.extend(np.std(mfccs, axis=1))   # 13 features
                features.extend(np.max(mfccs, axis=1))   # 13 features
                features.extend(np.min(mfccs, axis=1))   # 13 features
            except:
                features.extend(np.zeros(52))
            
            # Spectral features
            try:
                spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=self.sr)[0]
                features.append(np.mean(spectral_centroids))
                features.append(np.std(spectral_centroids))
            except:
                features.extend([0.0, 0.0])
            
            # Zero crossing rate
            try:
                zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
                features.append(np.mean(zcr))
                features.append(np.std(zcr))
            except:
                features.extend([0.0, 0.0])
            
            # RMS Energy
            try:
                rms = librosa.feature.rms(y=audio_data)[0]
                features.append(np.mean(rms))
                features.append(np.std(rms))
            except:
                features.extend([0.0, 0.0])
            
            # Pad to ensure consistent length
            while len(features) < 58:
                features.append(0.0)
            
            return np.array(features[:58])  # Ensure consistent length
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return np.zeros(58)

class SimpleAnimalClassifier:
    """Simplified real-time animal audio classification system"""
    
    def __init__(self, audio_dir: str, model_path: str = "simple_animal_classifier.pkl"):
        self.audio_dir = audio_dir
        self.model_path = model_path
        self.feature_extractor = SimpleAudioFeatureExtractor()
        self.scaler = StandardScaler()
        self.model = None
        self.animal_classes = []
        self.reference_features = {}
        self.is_listening = False
        self.audio_buffer = []
        self.buffer_duration = 3.0
        self.sample_rate = 22050
        
        self.setup_logging()
        self.load_or_train_model()
    
    def setup_logging(self):
        """Setup logging for predictions"""
        log_filename = f"animal_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Simple Animal Audio Classifier initialized")
    
    def extract_animal_name(self, filename: str) -> str:
        """Extract animal name from filename"""
        name = os.path.splitext(filename)[0]
        if name.endswith('A') or name.endswith('B'):
            name = name[:-1]
        return name
    
    def load_reference_audio(self) -> Dict[str, List[np.ndarray]]:
        """Load all reference audio files"""
        audio_files = [f for f in os.listdir(self.audio_dir) if f.endswith('.mp3')]
        audio_data = {}
        
        print(f"Loading {len(audio_files)} reference audio files...")
        
        for filename in audio_files:
            filepath = os.path.join(self.audio_dir, filename)
            animal_name = self.extract_animal_name(filename)
            
            try:
                audio, sr = librosa.load(filepath, sr=self.sample_rate)
                if animal_name not in audio_data:
                    audio_data[animal_name] = []
                audio_data[animal_name].append(audio)
                print(f"✓ Loaded {filename} -> {animal_name}")
            except Exception as e:
                print(f"✗ Error loading {filename}: {e}")
        
        self.animal_classes = sorted(audio_data.keys())
        print(f"Found {len(self.animal_classes)} animal classes")
        return audio_data
    
    def prepare_training_data(self, audio_data: Dict[str, List[np.ndarray]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data"""
        X = []
        y = []
        
        print("Extracting features...")
        
        for animal_name, audio_list in audio_data.items():
            class_idx = self.animal_classes.index(animal_name)
            
            for i, audio in enumerate(audio_list):
                print(f"  Processing {animal_name} sample {i+1}/{len(audio_list)}")
                
                # Extract features from original audio
                features = self.feature_extractor.extract_features(audio)
                X.append(features)
                y.append(class_idx)
                
                # Simple augmentation - add slight noise
                try:
                    noisy_audio = audio + 0.005 * np.random.randn(len(audio))
                    features_noisy = self.feature_extractor.extract_features(noisy_audio)
                    X.append(features_noisy)
                    y.append(class_idx)
                except:
                    pass
        
        print(f"Generated {len(X)} training samples")
        return np.array(X), np.array(y)
    
    def train_model(self, X: np.ndarray, y: np.ndarray):
        """Train the classification model"""
        print("Training model...")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Use Random Forest - simple and effective
        self.model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            max_depth=10,
            min_samples_split=5
        )
        self.model.fit(X_scaled, y)
        
        # Store reference features for similarity matching
        for i, animal_name in enumerate(self.animal_classes):
            class_features = X_scaled[y == i]
            self.reference_features[animal_name] = np.mean(class_features, axis=0)
        
        print("Model training completed!")
    
    def load_or_train_model(self):
        """Load existing model or train new one"""
        if os.path.exists(self.model_path):
            print("Loading existing model...")
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                    self.animal_classes = data['classes']
                    self.reference_features = data['reference_features']
                print("✓ Model loaded successfully!")
                return
            except Exception as e:
                print(f"✗ Error loading model: {e}, training new one...")
        
        # Train new model
        audio_data = self.load_reference_audio()
        X, y = self.prepare_training_data(audio_data)
        self.train_model(X, y)
        
        # Save model
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'classes': self.animal_classes,
                    'reference_features': self.reference_features
                }, f)
            print(f"✓ Model saved to {self.model_path}")
        except Exception as e:
            print(f"✗ Error saving model: {e}")
    
    def predict_animal(self, audio_data: np.ndarray) -> List[Tuple[str, float]]:
        """Predict animal from audio with confidence scores"""
        try:
            # Extract features
            features = self.feature_extractor.extract_features(audio_data)
            features_scaled = self.scaler.transform([features])
            
            # Get prediction probabilities
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(features_scaled)[0]
            else:
                # Fallback if no predict_proba
                prediction = self.model.predict(features_scaled)[0]
                probabilities = np.zeros(len(self.animal_classes))
                probabilities[prediction] = 1.0
            
            # Combine with similarity scores
            similarities = {}
            for i, animal_name in enumerate(self.animal_classes):
                if animal_name in self.reference_features:
                    ref_features = self.reference_features[animal_name]
                    similarity = cosine_similarity([features_scaled[0]], [ref_features])[0][0]
                    # Combine model prediction with similarity
                    combined_score = 0.7 * probabilities[i] + 0.3 * similarity
                    similarities[animal_name] = max(0, combined_score)
                else:
                    similarities[animal_name] = probabilities[i]
            
            # Sort by score and return top 3
            sorted_predictions = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            return sorted_predictions[:3]
            
        except Exception as e:
            print(f"Error in prediction: {e}")
            return [("Unknown", 0.0), ("Unknown", 0.0), ("Unknown", 0.0)]
    
    def audio_callback(self, indata, frames, time, status):
        """Callback for real-time audio input"""
        if status:
            print(f"Audio status: {status}")
        
        # Convert to mono
        if len(indata.shape) > 1:
            audio_chunk = np.mean(indata, axis=1)
        else:
            audio_chunk = indata.flatten()
        
        # Add to buffer
        self.audio_buffer.extend(audio_chunk)
        
        # Keep buffer at desired duration
        max_buffer_size = int(self.buffer_duration * self.sample_rate)
        if len(self.audio_buffer) > max_buffer_size:
            self.audio_buffer = self.audio_buffer[-max_buffer_size:]
    
    def start_listening(self):
        """Start real-time audio classification"""
        print(f"\n🎧 Starting real-time animal sound classification...")
        print(f"📊 Target animals: {', '.join(self.animal_classes)}")
        print(f"🔊 Listening for {self.buffer_duration} seconds per prediction...")
        print("🎯 Press Ctrl+C to stop\n")
        
        self.is_listening = True
        self.audio_buffer = []
        
        try:
            with sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=1024
            ):
                while self.is_listening:
                    time.sleep(self.buffer_duration)
                    
                    if len(self.audio_buffer) >= int(self.buffer_duration * self.sample_rate):
                        audio_data = np.array(self.audio_buffer)
                        
                        # Check for meaningful audio
                        if np.max(np.abs(audio_data)) > 0.01:
                            predictions = self.predict_animal(audio_data)
                            
                            # Display results
                            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - 🎵 Audio Analysis:")
                            print("=" * 50)
                            
                            for i, (animal, confidence) in enumerate(predictions, 1):
                                confidence_percent = confidence * 100
                                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                                print(f"{emoji} #{i}: {animal:<15} ({confidence_percent:6.2f}%)")
                            
                            # Log prediction
                            top_prediction = predictions[0]
                            log_msg = f"TOP: {top_prediction[0]} ({top_prediction[1]*100:.2f}%) | ALL: {', '.join([f'{name}({conf*100:.1f}%)' for name, conf in predictions])}"
                            self.logger.info(log_msg)
                            
                            print("=" * 50)
                        else:
                            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - 🔇 Low audio level...")
                        
                        self.audio_buffer = []
                        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping audio classification...")
            self.is_listening = False
        except Exception as e:
            print(f"\n❌ Error during audio capture: {e}")
            self.is_listening = False

def main():
    """Main function"""
    audio_dir = "ECE4191 - Potential Audio Targets"
    
    if not os.path.exists(audio_dir):
        print(f"❌ Audio directory '{audio_dir}' not found!")
        return
    
    print("🐨 Australian Animal Audio Classifier (Simple Version)")
    print("=" * 60)
    
    classifier = SimpleAnimalClassifier(audio_dir)
    classifier.start_listening()

if __name__ == "__main__":
    main()
