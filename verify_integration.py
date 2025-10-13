#!/usr/bin/env python3
"""
Quick verification script to check all audio integration files are in place
"""

import os
import sys

print("="*70)
print("AUDIO INTEGRATION - FILE VERIFICATION")
print("="*70)

# Expected files
required_files = {
    'config.py': 'Configuration file',
    'high_accuracy_classifier.py': 'CRNN model interface',
    'deviceControl.py': 'GUI integration (modified)',
    'test_integration.py': 'Test suite',
    'models/animal_classifier_best.h5': 'Trained CRNN model',
    'models/label_mapping.json': 'Class label mapping',
}

all_present = True

print("\nChecking required files:\n")
for filepath, description in required_files.items():
    exists = os.path.exists(filepath)
    size = os.path.getsize(filepath) if exists else 0
    
    if exists:
        if size > 1000000:  # > 1MB
            size_str = f"{size / 1000000:.1f} MB"
        elif size > 1000:  # > 1KB
            size_str = f"{size / 1000:.1f} KB"
        else:
            size_str = f"{size} bytes"
        
        print(f"✅ {filepath:<45} ({size_str})")
        print(f"   → {description}")
    else:
        print(f"❌ {filepath:<45} MISSING!")
        print(f"   → {description}")
        all_present = False

print("\n" + "="*70)

if all_present:
    print("✅ ALL REQUIRED FILES PRESENT!")
    print("\nNext steps:")
    print("  1. Run tests: python test_integration.py")
    print("  2. Launch GUI: python gui.py")
    print("  3. Start audio detection and test with animal sounds")
else:
    print("❌ SOME FILES ARE MISSING!")
    print("\nTo fix:")
    print("  1. Ensure you're in GUI_integration/ECE4191/ directory")
    print("  2. Check if model files exist in models/ directory")
    print("  3. Copy model files if needed:")
    print("     cp ../../models/*.h5 models/")
    print("     cp ../../models/*.json models/")

print("="*70)

# Check Python imports
print("\nChecking Python dependencies:\n")

dependencies = [
    'numpy',
    'tensorflow',
    'librosa',
    'tkinter',
]

import_errors = []
for module in dependencies:
    try:
        if module == 'tkinter':
            import tkinter
        else:
            __import__(module)
        print(f"✅ {module}")
    except ImportError as e:
        print(f"❌ {module} - {e}")
        import_errors.append(module)

print("\n" + "="*70)

if import_errors:
    print("❌ MISSING DEPENDENCIES!")
    print(f"\nInstall missing modules:")
    print(f"  pip install {' '.join(import_errors)}")
else:
    print("✅ ALL DEPENDENCIES INSTALLED!")

print("="*70)

sys.exit(0 if (all_present and not import_errors) else 1)
