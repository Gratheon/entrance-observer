import platform
import cv2
import os
import time

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

def apply_camera_properties(camera, properties):
    """Applies a dictionary of properties to the camera."""
    prop_map = {
        "brightness": cv2.CAP_PROP_BRIGHTNESS,
        "contrast": cv2.CAP_PROP_CONTRAST,
        "saturation": cv2.CAP_PROP_SATURATION,
        "gain": cv2.CAP_PROP_GAIN,
        "exposure": cv2.CAP_PROP_EXPOSURE,
        "jpeg_quality": getattr(cv2, 'CAP_PROP_JPEG_QUALITY', None),
        "white_balance_temperature": getattr(cv2, 'CAP_PROP_WHITE_BALANCE_TEMPERATURE', None),
        "gamma": getattr(cv2, 'CAP_PROP_GAMMA', None),
        "sharpness": getattr(cv2, 'CAP_PROP_SHARPNESS', None),
        "backlight": getattr(cv2, 'CAP_PROP_BACKLIGHT', None),
    }

    for prop_name, value in properties.items():
        prop = prop_map.get(prop_name)
        
        # Fallback for white balance temperature
        if prop is None and prop_name == "white_balance_temperature":
            prop = getattr(cv2, 'CAP_PROP_TEMPERATURE', None)

        if prop is not None:
            camera.set(prop, value)
            time.sleep(0.1)
            actual_value = camera.get(prop)
            print(f"✅ {prop_name.capitalize()} set to {actual_value} (requested: {value})")
        else:
            print(f"⚠️ Unknown or unsupported camera property: {prop_name}")

def initialize_camera(device, backend, width, height, fps, properties):
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
        
        def set_camera_property(prop, value, name):
            camera.set(prop, value)
            time.sleep(0.1) # Give camera time to apply setting
            actual_value = camera.get(prop)
            # For some properties, the value might not be set exactly as requested
            # We check if it's close enough or in a valid range
            if abs(actual_value - value) > 0.1:
                 # Special case for auto-exposure, where 0.25 means manual mode (often read back as 1)
                if prop == cv2.CAP_PROP_AUTO_EXPOSURE and value == 0.25 and actual_value == 1.0:
                    print(f"✅ {name} set to Manual Mode")
                else:
                    print(f"⚠️ Failed to set {name}: requested={value}, actual={actual_value}")
            else:
                print(f"✅ {name} set to {actual_value}")

        # Disable auto-exposure and auto-white-balance for consistent performance
        set_camera_property(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25, "Auto Exposure")  # Manual exposure
        
        # Set pixel format for better performance
        set_camera_property(cv2.CAP_PROP_CONVERT_RGB, 1, "Convert RGB")
        
        # Apply dynamic properties
        apply_camera_properties(camera, properties)
        
        set_camera_property(cv2.CAP_PROP_AUTOFOCUS, 0, "Autofocus") # Disable autofocus
        
        # Additional performance optimizations
        try:
            # Try to reduce JPEG quality for better performance
            set_camera_property(cv2.CAP_PROP_JPEG_QUALITY, 100, "JPEG Quality")  # Lower quality = faster processing
        except:
            pass
    
    # Verify actual settings
    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = camera.get(cv2.CAP_PROP_FPS)
    actual_fourcc = int(camera.get(cv2.CAP_PROP_FOURCC))
    
    print(f"📐 Requested: {width}x{height}@{fps}fps")
    print(f"📐 Actual: {actual_width}x{actual_height}@{actual_fps}fps")
    print(f"📐 Codec: {chr(actual_fourcc & 0xFF)}{chr((actual_fourcc >> 8) & 0xFF)}{chr((actual_fourcc >> 16) & 0xFF)}{chr((actual_fourcc >> 24) & 0xFF)}")
    
    return camera
