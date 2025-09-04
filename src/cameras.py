import platform
import cv2
import os

def list_available_cameras():
    """List available cameras on the system"""
    system = platform.system().lower()
    available_cameras = []

    # Suppress OpenCV warnings during camera detection
    original_log_level = cv2.getLogLevel()
    cv2.setLogLevel(3)  # 3 = ERROR level, suppress warnings

    try:
        if system == "darwin":  # macOS
            # Try camera indices, but stop when we get consecutive failures
            consecutive_failures = 0
            for i in range(10):  # Check up to 10 cameras
                try:
                    cap = cv2.VideoCapture(i, cv2.CAP_AVFOUNDATION)
                    if cap.isOpened():
                        available_cameras.append(i)
                        consecutive_failures = 0
                        cap.release()
                    else:
                        consecutive_failures += 1
                        # Stop searching after 3 consecutive failures
                        if consecutive_failures >= 3:
                            break
                except Exception:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        break
        elif system == "linux":
            # Check for video devices in /dev/
            for i in range(10):
                device_path = f"/dev/video{i}"
                if os.path.exists(device_path):
                    try:
                        cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
                        if cap.isOpened():
                            available_cameras.append(device_path)
                            cap.release()
                    except Exception:
                        pass
    finally:
        # Restore original log level
        cv2.setLogLevel(original_log_level)

    return available_cameras


def get_default_camera_config():
    system = platform.system().lower()
    device_from_env = os.getenv("CAMERA_DEVICE")

    if device_from_env:
        # If the device is a number, convert it to an integer
        if device_from_env.isdigit():
            device = int(device_from_env)
        else:
            device = device_from_env
    elif system == "darwin":  # macOS
        device = 0
    elif system == "linux":
        device = "/dev/video2"
    else:  # Windows or other
        device = 0

    if system == "darwin":
        backend = cv2.CAP_AVFOUNDATION
    elif system == "linux":
        backend = cv2.CAP_V4L2
    elif system == "windows":
        backend = cv2.CAP_DSHOW
    else:
        backend = cv2.CAP_ANY

    return {
        "device": device,
        "backend": backend
    }

def initialize_camera(device, backend, width, height, fps):
    """
    Initializes the camera using the specified backend with optimized settings.
    """
    print(f"🔌 Initializing camera with device={device} and backend={backend}...")
    camera = cv2.VideoCapture(device, backend)
    
    if not camera.isOpened():
        print(f"⚠️ Failed to open camera.")
        return camera
    
    # Optimize camera settings for better performance
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer to reduce latency
    
    # Force MJPEG format - critical for performance (YUYV only supports 2 FPS)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    
    # Verify MJPEG format was set successfully
    actual_fourcc_before = int(camera.get(cv2.CAP_PROP_FOURCC))
    fourcc_str_before = ''.join([chr((actual_fourcc_before >> 8*i) & 0xFF) for i in range(4)])
    print(f"📐 Format before resolution: {fourcc_str_before}")
    
    # Set resolution and FPS
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    camera.set(cv2.CAP_PROP_FPS, fps)
    
    # Additional V4L2 optimizations for Linux
    if backend == cv2.CAP_V4L2:
        # Critical: Set MJPEG format again after resolution to ensure it sticks
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        # Disable auto-exposure and auto-white-balance for consistent performance
        # camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
        # camera.set(cv2.CAP_PROP_EXPOSURE, -6)  # Fast exposure setting
        
        # # Set pixel format for better performance
        # camera.set(cv2.CAP_PROP_CONVERT_RGB, 1)
        
        # # Optimize for speed over quality
        # camera.set(cv2.CAP_PROP_BRIGHTNESS, 120) # Default is 128
        # camera.set(cv2.CAP_PROP_CONTRAST, 95) # Default is 128
        # camera.set(cv2.CAP_PROP_SATURATION, 128) # Default is 128
        # camera.set(cv2.CAP_PROP_GAIN, 0) # Disable gain
        # camera.set(cv2.CAP_PROP_AUTOFOCUS, 0) # Disable autofocus
        
        # # Additional performance optimizations
        # try:
        #     # Try to reduce JPEG quality for better performance
        #     camera.set(cv2.CAP_PROP_JPEG_QUALITY, 50)  # Lower quality = faster processing
        # except:
        #     pass
    
    # Verify actual settings
    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = camera.get(cv2.CAP_PROP_FPS)
    actual_fourcc = int(camera.get(cv2.CAP_PROP_FOURCC))
    
    print(f"📐 Requested: {width}x{height}@{fps}fps")
    print(f"📐 Actual: {actual_width}x{actual_height}@{actual_fps}fps")
    print(f"📐 Codec: {chr(actual_fourcc & 0xFF)}{chr((actual_fourcc >> 8) & 0xFF)}{chr((actual_fourcc >> 16) & 0xFF)}{chr((actual_fourcc >> 24) & 0xFF)}")
    
    return camera
