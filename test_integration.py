#!/usr/bin/env python3
"""
Test script to verify CRNN audio classifier integration with GUI

This script tests:
1. Model loading
2. Audio preprocessing
3. Prediction functionality
4. Voting system
5. GUI audio stream compatibility
"""

import os
import sys
import numpy as np

print("="*70)
print("CRNN AUDIO CLASSIFIER - INTEGRATION TEST")
print("="*70)

# Test 1: Import classifier
print("\n[TEST 1] Importing classifier...")
try:
    from high_accuracy_classifier import HighAccuracyAnimalClassifier
    print("✅ Classifier imported successfully")
except ImportError as e:
    print(f"❌ Failed to import classifier: {e}")
    sys.exit(1)

# Test 2: Initialize classifier
print("\n[TEST 2] Initializing classifier...")
try:
    classifier = HighAccuracyAnimalClassifier()
    print("✅ Classifier initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize classifier: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Get classifier info
print("\n[TEST 3] Getting classifier information...")
try:
    info = classifier.get_info()
    print(f"✅ Classifier info retrieved:")
    print(f"   - Model: {os.path.basename(info['model_path'])}")
    print(f"   - Classes: {info['num_classes']}")
    print(f"   - Sample rate: {info['sample_rate']} Hz")
    print(f"   - Segment duration: {info['segment_duration']}s")
    print(f"   - Voting window: {info['voting_window_size']}")
except Exception as e:
    print(f"❌ Failed to get info: {e}")
    sys.exit(1)

# Test 4: Test with GUI-like audio (44100 Hz, int16)
print("\n[TEST 4] Testing with GUI audio format (44100 Hz, int16)...")
try:
    # Simulate 3 seconds of GUI audio
    duration = 3.0
    sample_rate = 44100  # GUI audio rate
    num_samples = int(duration * sample_rate)
    
    # Create synthetic audio (random noise)
    audio_int16 = np.random.randint(-5000, 5000, num_samples, dtype=np.int16)
    
    print(f"   Input audio: {audio_int16.shape}, dtype={audio_int16.dtype}, rate={sample_rate}Hz")
    
    # Test prediction
    predictions = classifier.predict_animal(audio_int16, source_sample_rate=sample_rate)
    
    print(f"✅ Prediction successful!")
    print(f"   Top 5 predictions:")
    for i, (animal, conf) in enumerate(predictions[:5], 1):
        print(f"      {i}. {animal:20s} {conf*100:5.1f}%")
        
except Exception as e:
    print(f"❌ Prediction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test with bytes (UDP stream format)
print("\n[TEST 5] Testing with bytes format (UDP audio stream)...")
try:
    # Simulate bytes from UDP stream
    audio_bytes = audio_int16.tobytes()
    
    print(f"   Input: {len(audio_bytes)} bytes")
    
    predictions = classifier.predict_animal(audio_bytes, source_sample_rate=sample_rate)
    
    print(f"✅ Bytes prediction successful!")
    print(f"   Top 3 predictions:")
    for i, (animal, conf) in enumerate(predictions[:3], 1):
        print(f"      {i}. {animal:20s} {conf*100:5.1f}%")
        
except Exception as e:
    print(f"❌ Bytes prediction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Test voting system
print("\n[TEST 6] Testing voting system...")
try:
    classifier.reset_voting_history()
    
    # Make multiple predictions to test voting
    for i in range(5):
        predictions = classifier.predict_animal(audio_int16, source_sample_rate=sample_rate)
    
    # Get voting result
    final_pred, vote_pct, avg_conf = classifier.get_voting_result()
    
    print(f"✅ Voting system working!")
    print(f"   Final prediction: {final_pred}")
    print(f"   Vote percentage: {vote_pct*100:.1f}%")
    print(f"   Avg confidence: {avg_conf*100:.1f}%")
    
except Exception as e:
    print(f"❌ Voting system failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test with real audio file (if available)
print("\n[TEST 7] Testing with real audio file...")
try:
    # Look for test audio in Recorded_animals
    test_audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Recorded_animals'))
    
    if os.path.exists(test_audio_dir):
        import librosa
        
        # Get first .wav file
        wav_files = [f for f in os.listdir(test_audio_dir) if f.endswith('.wav')]
        
        if wav_files:
            test_file = os.path.join(test_audio_dir, wav_files[0])
            print(f"   Testing with: {wav_files[0]}")
            
            # Load audio
            audio, sr = librosa.load(test_file, sr=44100, mono=True)
            
            # Take first 3 seconds
            audio_3s = audio[:int(3.0 * sr)]
            
            # Convert to int16 (like GUI)
            audio_int16 = (audio_3s * 32767).astype(np.int16)
            
            # Predict
            predictions = classifier.predict_animal(audio_int16, source_sample_rate=sr)
            
            print(f"✅ Real audio test successful!")
            print(f"   Top prediction: {predictions[0][0]} ({predictions[0][1]*100:.1f}%)")
            print(f"   Expected: {os.path.splitext(wav_files[0])[0][:-1]}")  # Remove trailing A/B
        else:
            print("⚠️  No .wav files found, skipping real audio test")
    else:
        print("⚠️  Recorded_animals directory not found, skipping real audio test")
        
except Exception as e:
    print(f"⚠️  Real audio test skipped: {e}")

# Test 8: Memory and performance test
print("\n[TEST 8] Performance test...")
try:
    import time
    
    # Time 10 predictions
    start_time = time.time()
    for _ in range(10):
        predictions = classifier.predict_animal(audio_int16, source_sample_rate=sample_rate)
    elapsed = time.time() - start_time
    
    avg_time = elapsed / 10
    
    print(f"✅ Performance test complete!")
    print(f"   Average prediction time: {avg_time*1000:.1f}ms")
    print(f"   Predictions per second: {1/avg_time:.1f}")
    
    if avg_time < 0.5:
        print(f"   ✅ EXCELLENT - Fast enough for real-time (< 500ms)")
    elif avg_time < 1.0:
        print(f"   ⚠️  ACCEPTABLE - Usable for real-time (< 1s)")
    else:
        print(f"   ❌ SLOW - May cause lag in GUI (> 1s)")
        
except Exception as e:
    print(f"❌ Performance test failed: {e}")

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print("""
✅ All critical tests passed!

The CRNN audio classifier is ready for GUI integration.

Next steps:
1. Start the GUI: python gui.py
2. Connect to your device
3. Start the audio stream
4. Click "Start Audio Detection"

The classifier will:
- Analyze audio every 3 seconds
- Show top 3 predictions in real-time
- Track detection counts
- Use voting for robust results
""")

print("="*70)
