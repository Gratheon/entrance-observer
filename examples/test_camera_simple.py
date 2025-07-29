#!/usr/bin/env python3
"""
Simple camera test script for macOS support verification
"""
import cv2
import platform
import time

def test_camera_basic():
    """Test basic camera functionality"""
    print(f"Testing camera on {platform.system()}")
    
    # Suppress OpenCV warnings
    cv2.setLogLevel(3)  # 3 = ERROR level, suppress warnings
    
    # Determine backend based on platform
    system = platform.system().lower()
    if system == "darwin":
        backend = cv2.CAP_AVFOUNDATION
        device = 0
    elif system == "linux":
        backend = cv2.CAP_V4L2
        device = "/dev/video0"
    else:
        backend = cv2.CAP_ANY
        device = 0
    
    print(f"Trying to open camera {device} with backend {backend}")
    
    # Try to open camera
    cap = cv2.VideoCapture(device, backend)
    
    if not cap.isOpened():
        print("❌ Failed to open camera")
        return False
    
    print("✅ Camera opened successfully")
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Camera properties: {width}x{height} @ {fps} FPS")
    
    # Try to capture a few frames
    frames_captured = 0
    for i in range(5):
        ret, frame = cap.read()
        if ret:
            frames_captured += 1
            print(f"Frame {i+1}: {frame.shape}")
        else:
            print(f"Frame {i+1}: Failed to capture")
        time.sleep(0.1)
    
    cap.release()
    
    if frames_captured > 0:
        print(f"✅ Successfully captured {frames_captured}/5 frames")
        return True
    else:
        print("❌ Failed to capture any frames")
        return False

if __name__ == "__main__":
    print("Simple Camera Test")
    print("=" * 30)
    success = test_camera_basic()
    print("\nTest completed:", "✅ PASSED" if success else "❌ FAILED")
