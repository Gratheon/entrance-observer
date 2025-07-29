#!/usr/bin/env python3
"""
Test script to verify camera functionality on different platforms
"""
import cv2
import platform
import sys
import os

# Add the current directory to path to import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import list_available_cameras, get_default_camera_config


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


def test_specific_camera(device_path):
    """Test a specific camera device"""
    print(f"\nTesting specific camera: {device_path}")
    print("-" * 30)
    
    system = platform.system().lower()
    if system == "darwin":
        backend = cv2.CAP_AVFOUNDATION
        # Convert string to int if it's a digit
        try:
            device = int(device_path) if isinstance(device_path, str) and device_path.isdigit() else device_path
        except ValueError:
            device = device_path
    elif system == "linux":
        backend = cv2.CAP_V4L2
        device = device_path
    else:
        backend = cv2.CAP_ANY
        device = device_path
    
    cap = cv2.VideoCapture(device, backend)
    
    if cap.isOpened():
        print(f"✓ Camera {device_path} opened successfully with backend {backend}")
        
        # Test frame capture
        ret, frame = cap.read()
        if ret:
            print(f"✓ Frame capture successful, shape: {frame.shape}")
        else:
            print(f"✗ Frame capture failed")
        
        cap.release()
        return True
    else:
        print(f"✗ Failed to open camera {device_path}")
        return False


if __name__ == "__main__":
    print("Camera Detection and Testing Tool")
    print("=" * 50)
    
    # Test general camera detection
    success = test_camera_detection()
    
    # Test specific camera if provided as argument
    if len(sys.argv) > 1:
        device_path = sys.argv[1]
        test_specific_camera(device_path)
    
    print("\nTest completed!")
