#!/bin/bash
# Quick Start Script for CRNN Audio Classifier GUI Integration

echo "=========================================="
echo "CRNN Audio Classifier - Quick Start"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "high_accuracy_classifier.py" ]; then
    echo "❌ Error: Please run this script from GUI_integration/ECE4191/"
    echo "   cd GUI_integration/ECE4191"
    exit 1
fi

echo "Step 1: Checking dependencies..."
python3 -c "import tensorflow; import librosa; import numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Missing dependencies. Installing..."
    pip install tensorflow librosa numpy sounddevice soundfile
else
    echo "✅ Dependencies OK"
fi

echo ""
echo "Step 2: Checking model files..."
if [ ! -f "../../models/animal_classifier_best.h5" ]; then
    echo "❌ Model not found!"
    echo "   Please train the model first:"
    echo "   cd ../.."
    echo "   python train_model.py"
    exit 1
else
    echo "✅ Model found"
fi

if [ ! -f "../../models/label_mapping.json" ]; then
    echo "❌ Label mapping not found!"
    echo "   Please train the model first"
    exit 1
else
    echo "✅ Label mapping found"
fi

echo ""
echo "Step 3: Running integration tests..."
python3 test_integration.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Integration tests failed!"
    echo "   Please check errors above"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ All checks passed!"
echo "=========================================="
echo ""
echo "Ready to start the GUI!"
echo ""
echo "To launch:"
echo "  python3 gui.py"
echo ""
echo "Then:"
echo "  1. Go to 'Connection Setup' and connect to Pi"
echo "  2. Go to 'Device Control'"
echo "  3. Click 'Start Stream'"
echo "  4. Click 'Start Audio Detection'"
echo ""
echo "Happy detecting! 🐨🦘🦆"
echo ""
