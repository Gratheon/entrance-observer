import os
import time
import datetime
import cv2
import platform

from src.cameras import list_available_cameras, get_default_camera_config
from uploader import upload_file_async, delete_old_mp4_files
from counter import count_bees_async

# enable GPU acceleration
cv2.CAP_GSTREAMER


def startObserverClient():
    FPS = int(os.getenv("FPS", 30))
    WIDTH_PX = int(os.getenv("WIDTH_PX", 640))
    HEIGHT_PX = int(os.getenv("HEIGHT_PX", 480))

    # List available cameras for debugging
    print(f"Running on {platform.system()}")
    available_cameras = list_available_cameras()
    print(f"Available cameras: {available_cameras}")

    camera_config = get_default_camera_config()
    device = camera_config["device"]
    backend = camera_config["backend"]
    
    # If default device is not available, use first available camera
    if available_cameras and device not in available_cameras:
        device = available_cameras[0]
        print(f"Default camera not available, using: {device}")


    print(f"Initializing camera with device: {device}, backend: {backend}")
    camera = cv2.VideoCapture(device, backend)

    if not camera.isOpened():
        print(f"Error: Could not open camera with device: {device}")
        
        # Try available cameras as fallback
        if available_cameras:
            print("Trying available cameras as fallback...")
            for alt_device in available_cameras:
                if alt_device != device:  # Skip the one we already tried
                    print(f"Trying camera: {alt_device}")
                    camera = cv2.VideoCapture(alt_device, backend)
                    if camera.isOpened():
                        print(f"Successfully opened camera: {alt_device}")
                        device = alt_device
                        break
                    camera.release()
        
        if not camera.isOpened():
            print("Failed to open any camera")
            return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH_PX)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT_PX)
    camera.set(cv2.CAP_PROP_FPS, 30)

    cv2.namedWindow("Preview", cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            timestamp = int(datetime.datetime.now().timestamp())
            output_file = f'./videos/{timestamp}.mp4'
            out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (WIDTH_PX, HEIGHT_PX))

            start_time = time.time()
            while True:
                ret, frame = camera.read()
                if not ret:
                    print('Error: Failed to capture frame')
                    break
                out.write(frame)
                cv2.imshow("Preview", frame)

                if cv2.waitKey(1) & 0xFF == ord('q') or time.time() - start_time >= 10:
                    out.release()
                    break

            print(f"Video saved to {output_file}")
            # count_bees_async(output_file)
            # upload_file_async(output_file)
            # delete_old_mp4_files()


    except KeyboardInterrupt:
        print("Recording and uploading stopped by user")

    finally:
        os.remove(output_file)
        camera.release()
        cv2.destroyAllWindows()


startObserverClient()
