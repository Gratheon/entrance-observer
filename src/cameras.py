import platform
import cv2

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

    if system == "darwin":  # macOS
        return {
            "device": 0,  # Default camera index on macOS
            "backend": cv2.CAP_AVFOUNDATION
        }
    elif system == "linux":
        return {
            "device": "/dev/video2",
            "backend": cv2.CAP_V4L2
        }
    else:  # Windows or other
        return {
            "device": 0,
            "backend": cv2.CAP_DSHOW if system == "windows" else cv2.CAP_ANY
        }
