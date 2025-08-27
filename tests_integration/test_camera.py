#!/usr/bin/env python3
"""
Test script to verify camera functionality on different platforms
"""
import cv2
import platform
import sys
import os

# Add the current directory to path to import from main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cameras import list_available_cameras, get_default_camera_config


def test_camera_detection():
    """Test camera detection functionality"""
    print(f"Testing camera detection on {platform.system()}")
    print("-" * 50)
    
    # List available cameras
    available_cameras = list_available_cameras()
    print(f"Available cameras: {available_cameras}")
    
    if not available_cameras:
        print("No cameras detected!")
        return False
    
    # Get default configuration
    config = get_default_camera_config()
    print(f"Default camera config: {config}")
    
    # Test opening each available camera
    for camera_device in available_cameras:
        print(f"\nTesting camera: {camera_device}")
        
        # Determine backend based on platform
        system = platform.system().lower()
        if system == "darwin":
            backend = cv2.CAP_AVFOUNDATION
        elif system == "linux":
            backend = cv2.CAP_V4L2
        else:
            backend = cv2.CAP_ANY
        
        cap = cv2.VideoCapture(camera_device, backend)
        
        if cap.isOpened():
            # Get camera properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"  ✓ Camera opened successfully")
            print(f"  Resolution: {int(width)}x{int(height)}")
            print(f"  FPS: {fps}")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"  ✓ Frame capture successful")
                print(f"  Frame shape: {frame.shape}")
            else:
                print(f"  ✗ Frame capture failed")
            
            cap.release()
        else:
            print(f"  ✗ Failed to open camera")
    
    return True
