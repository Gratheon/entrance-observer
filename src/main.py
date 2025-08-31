import os
import time
import datetime
import cv2
import platform
from flask import Flask, Response, render_template_string
import threading
from ultralytics import YOLO

from src.cameras import list_available_cameras, get_default_camera_config
from uploader import upload_file_async, delete_old_mp4_files
from counter import count_bees_async

# enable GPU acceleration
cv2.CAP_GSTREAMER

app = Flask(__name__)
video_frame = None
yolo_frame = None
frame_lock = threading.Lock()

weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','weights', 'best.pt'))
model = YOLO(weights_path)

def generate_frames(get_frame):
    while True:
        with frame_lock:
            frame = get_frame()
            if frame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')

@app.route("/")
def index():
    return render_template_string("""
   <html>
     <head>
       <title>Video Streaming Demonstration</title>
     </head>
     <body>
       <h1>Video Streaming Demonstration</h1>
       <table>
         <tr>
           <td><img src="{{ url_for('video_feed') }}"></td>
           <td><img src="{{ url_for('video_feed_yolo') }}"></td>
         </tr>
       </table>
     </body>
   </html>
   """)

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(lambda: video_frame),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/video_feed_yolo")
def video_feed_yolo():
    return Response(generate_frames(lambda: yolo_frame),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

def startObserverClient():
    global video_frame, yolo_frame
    FPS = int(os.getenv("FPS", 30))
    WIDTH_PX = int(os.getenv("WIDTH_PX", 640))
    HEIGHT_PX = int(os.getenv("HEIGHT_PX", 480))

    print(f"Running on {platform.system()}")
    available_cameras = list_available_cameras()
    print(f"Available cameras: {available_cameras}")

    camera_config = get_default_camera_config()
    device = camera_config["device"]
    backend = camera_config["backend"]
    
    if available_cameras and device not in available_cameras:
        device = available_cameras[0]
        print(f"Default camera not available, using: {device}")

    print(f"Initializing camera with device: {device}, backend: {backend}")
    camera = cv2.VideoCapture(device, backend)

    if not camera.isOpened():
        print(f"Error: Could not open camera with device: {device}")
        if available_cameras:
            print("Trying available cameras as fallback...")
            for alt_device in available_cameras:
                if alt_device != device:
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

    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera's native resolution: {actual_width}x{actual_height}")

    aspect_ratio = actual_height / actual_width
    target_width = WIDTH_PX
    target_height = int(target_width * aspect_ratio)

    if target_height % 32 != 0:
        target_height = (target_height // 32) * 32
    
    print(f"Target resolution (adjusted for YOLO): {target_width}x{target_height}")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
    camera.set(cv2.CAP_PROP_FPS, FPS)

    try:
        while True:
            timestamp = int(datetime.datetime.now().timestamp())
            output_file = f'./videos/{timestamp}.mp4'
            debug_output_file = f'./videos/{timestamp}_detect.mp4'
            
            out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'avc1'), FPS, (target_width, target_height))
            
            if not out.isOpened():
                print("Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
                out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (target_width, target_height))
                if not out.isOpened():
                    print("Fallback codec 'mp4v' also failed. Exiting.")
                    break

            start_time = time.time()
            start_time_utc = datetime.datetime.utcnow()
            while True:
                ret, frame = camera.read()
                if not ret:
                    print('Error: Failed to capture frame')
                    break
                
                resized_frame = cv2.resize(frame, (target_width, target_height))
                
                results = model.track(resized_frame, persist=True)
                annotated_frame = results[0].plot()

                with frame_lock:
                    video_frame = resized_frame.copy()
                    yolo_frame = annotated_frame.copy()

                out.write(resized_frame)

                if time.time() - start_time >= 10:
                    out.release()
                    break

            print(f"Video saved to {output_file}")
            
            def upload_detect_file(file_path):
                print(f"Uploading debug file: {file_path}")
                upload_file_async(file_path, start_time_utc)

            count_bees_async(output_file, output_video_path=debug_output_file, on_complete=upload_detect_file)
            upload_file_async(output_file, start_time_utc)
            delete_old_mp4_files()

    except KeyboardInterrupt:
        print("Recording and uploading stopped by user")

    finally:
        camera.release()

if __name__ == '__main__':
    observer_thread = threading.Thread(target=startObserverClient)
    observer_thread.daemon = True
    observer_thread.start()
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
