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
    Initializes the camera with a hardware-accelerated GStreamer pipeline for USB cameras on Jetson.
    """
    # GStreamer pipeline for USB cameras, using autovideoconvert for maximum compatibility
    gstreamer_pipeline = (
        f"v4l2src device={device} ! "
        f"video/x-raw, width={width}, height={height}, framerate={fps}/1 ! "
        f"autovideoconvert ! "
        f"video/x-raw, format=BGR ! appsink"
    )
    
    print(f"🔌 Attempting to initialize camera with GStreamer pipeline for USB camera...")
    camera = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not camera.isOpened():
        print(f"⚠️ GStreamer pipeline failed. Falling back to default V4L2 backend.")
        camera = cv2.VideoCapture(device, backend)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Set properties again for the fallback
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        camera.set(cv2.CAP_PROP_FPS, fps)

    return camera
