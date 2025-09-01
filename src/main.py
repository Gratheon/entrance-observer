import os
import time
import datetime
import cv2
import platform
from flask import Flask, Response, render_template_string, jsonify, request
import threading
import logging
from ultralytics import YOLO
from collections import deque

from src.cameras import list_available_cameras, get_default_camera_config
from uploader import upload_file_async, delete_old_mp4_files
from counter import count_bees_async

# enable GPU acceleration
cv2.CAP_GSTREAMER

app = Flask(__name__)
video_frame = None
yolo_frame = None
frame_lock = threading.Lock()
bee_counts_history = deque(maxlen=3600)  # Store up to last 10h. 10*60*6 entries (1 hour if updated every 10 sec)

weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','weights', 'best.pt'))
logging.getLogger('ultralytics').setLevel(logging.WARNING)
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

from flask import send_from_directory

@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'img'), path)

@app.route("/")
def index():
    html = """
   <html>
     <head>
       <title>Entrance Observer</title>
       <style>
         body { 
           font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
           margin: 0; 
           padding: 0; 
           background-color: #f8f8f8; /* @color-gray-bg */
           display: flex;
           flex-direction: column;
           min-height: 100vh;
         }
         .header { 
           background: white; 
           border-bottom: 1px solid #c5c5c5; /* @color-gray-breadcrumbs-border */
           padding: 8px;
           text-align: center;
         }
         .header img { 
           height: 100px; 
           margin: 0 auto; 
           display: block; 
         }
         .container { 
           padding: 20px; 
           flex-grow: 1;
         }
         .video-container { 
           display: flex; 
           justify-content: center; 
           gap: 20px; 
           flex-wrap: wrap;
         }
         .toggle-container {
           text-align: center;
           margin-bottom: 20px;
         }
         .video-wrapper h2 {
           text-align: center;
           color: #424242; /* @color-gray-breadcrumbs-text */
           font-weight: 500;
         }
         .footer { 
           background-color: #ececec; /* @color-gray-breadcrumbs */
           border-top: 1px solid #c5c5c5; /* @color-gray-breadcrumbs-border */
           padding: 20px;
           box-sizing: border-box;
         }
         .footer ul {
           display: flex;
           justify-content: center;
           list-style: none;
           margin: 0;
           padding: 0;
         }
         .footer li {
           padding: 0 10px;
         }
         .footer a { 
           color: black; 
           text-decoration: none; 
         }
         .footer a:hover {
            text-decoration: underline;
         }
       </style>
     </head>
     <body>
       <div class="header">
         <a href="https://app.gratheon.com/apiaries" target="_blank">
            <img src="{{ url_for('send_img', path='gratheon.png') }}" alt="Gratheon Logo">
         </a>
       </div>
       <div class="container">
         <div class="toggle-container">
           <label>
             <input type="checkbox" id="feed-toggle">
             Show Live Feed
           </label>
         </div>
         <div class="video-container">
           <div class="video-wrapper">
             <div id="video-container" style="position: relative; display: inline-block;">
                <img id="video-feed-img" src="{{ url_for('video_feed_yolo') }}">
                <div id="detection-line" style="position: absolute; left: 0; width: 100%; height: 4px; background-color: red; cursor: pointer; top: {{ detection_line_coefficient * 100 }}%;"></div>
             </div>
           </div>
         </div>
         <div style="text-align: center; padding-top: 20px; font-size: 24px; color: #424242;">
           &darr; Hive Entrance &darr;
         </div>
         <div id="bee-counts-container" style="padding: 20px;">
           <h3 style="text-align: center; color: #424242; font-weight: 500;">Bee Traffic</h3>
           <table id="bee-counts-table" style="width: 100%; border-collapse: collapse;">
             <thead>
               <tr>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Incoming</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Outgoing</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Detected</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Time</th>
               </tr>
             </thead>
             <tbody>
             </tbody>
           </table>
         </div>
       </div>
       <script>
         function fetchBeeCounts() {
           fetch('/api/bee_counts')
             .then(response => response.json())
             .then(data => {
               const tableBody = document.querySelector('#bee-counts-table tbody');
               tableBody.innerHTML = '';
               data.forEach(count => {
                 const row = document.createElement('tr');
                 row.innerHTML = `
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.incoming}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.outgoing}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.detected}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.time}</td>
                 `;
                 tableBody.insertBefore(row, tableBody.firstChild);
               });
             });
         }
         setInterval(fetchBeeCounts, 10000);
         fetchBeeCounts();
       </script>
       <script>
         const feedToggle = document.getElementById('feed-toggle');
         const videoFeedImg = document.getElementById('video-feed-img');
         const liveFeedUrl = "{{ url_for('video_feed') }}";
         const yoloFeedUrl = "{{ url_for('video_feed_yolo') }}";

         feedToggle.addEventListener('change', () => {
           if (feedToggle.checked) {
             videoFeedImg.src = liveFeedUrl;
           } else {
             videoFeedImg.src = yoloFeedUrl;
           }
         });
       </script>
       <script>
         const detectionLine = document.getElementById('detection-line');
         const videoContainer = document.getElementById('video-container');
         let isDragging = false;

         detectionLine.addEventListener('mousedown', (e) => {
           isDragging = true;
         });

         videoContainer.addEventListener('mousemove', (e) => {
           if (isDragging) {
             const rect = videoContainer.getBoundingClientRect();
             const y = e.clientY - rect.top;
             const height = rect.height;
             let coefficient = y / height;
             if (coefficient < 0) coefficient = 0;
             if (coefficient > 1) coefficient = 1;
             detectionLine.style.top = `${coefficient * 100}%`;
           }
         });

         videoContainer.addEventListener('mouseup', (e) => {
           if (isDragging) {
             isDragging = false;
             const rect = videoContainer.getBoundingClientRect();
             const y = e.clientY - rect.top;
             const height = rect.height;
             let coefficient = y / height;
             if (coefficient < 0) coefficient = 0;
             if (coefficient > 1) coefficient = 1;
             
             fetch('/api/set_detection_line', {
               method: 'POST',
               headers: {
                 'Content-Type': 'application/json',
               },
               body: JSON.stringify({ coefficient: coefficient }),
             });
           }
         });
       </script>
       <div class="footer">
         <ul>
            <li><a href="https://gratheon.com/terms" target="_blank">Terms of Use</a></li>
            <li><a href="https://gratheon.com/privacy" target="_blank">Privacy policy</a></li>
            <li><a href="https://gratheon.com/docs/entrance-observer/" target="_blank">Docs</a></li>
         </ul>
       </div>
     </body>
   </html>
   """
    return render_template_string(html, detection_line_coefficient=detection_line_coefficient)

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(lambda: video_frame),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/video_feed_yolo")
def video_feed_yolo():
    return Response(generate_frames(lambda: yolo_frame),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/bee_counts")
def bee_counts():
    return jsonify(list(bee_counts_history))

detection_line_coefficient = float(os.getenv("DETECTION_LINE", 0.5))

@app.route("/api/set_detection_line", methods=['POST'])
def set_detection_line():
    global detection_line_coefficient
    data = request.get_json()
    detection_line_coefficient = data['coefficient']
    return jsonify(success=True)

def startObserverClient():
    global video_frame, yolo_frame
    FPS = int(os.getenv("FPS", 30))
    WIDTH_PX = int(os.getenv("WIDTH_PX", 640))
    HEIGHT_PX = int(os.getenv("HEIGHT_PX", 480))

    print(f"🖥️ Running on {platform.system()}")
    available_cameras = list_available_cameras()
    print(f"📷 Available cameras: {available_cameras}")

    camera_config = get_default_camera_config()
    device = camera_config["device"]
    backend = camera_config["backend"]
    
    if available_cameras and device not in available_cameras:
        device = available_cameras[0]
        print(f"⚠️ Default camera not available, using: {device}")

    print(f"🔌 Initializing camera with device: {device}, backend: {backend}")
    camera = cv2.VideoCapture(device, backend)

    if not camera.isOpened():
        print(f"❌ Error: Could not open camera with device: {device}")
        if available_cameras:
            print("🔄 Trying available cameras as fallback...")
            for alt_device in available_cameras:
                if alt_device != device:
                    print(f"🔄 Trying camera: {alt_device}")
                    camera = cv2.VideoCapture(alt_device, backend)
                    if camera.isOpened():
                        print(f"✅ Successfully opened camera: {alt_device}")
                        device = alt_device
                        break
                    camera.release()
        
        if not camera.isOpened():
            print("❌ Failed to open any camera")
            return

    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"ℹ️ Camera's native resolution: {actual_width}x{actual_height}")

    aspect_ratio = actual_height / actual_width
    target_width = WIDTH_PX
    target_height = int(target_width * aspect_ratio)

    if target_height % 32 != 0:
        target_height = (target_height // 32) * 32
    
    print(f"🎯 Target resolution (adjusted for YOLO): {target_width}x{target_height}")

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
                print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
                out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (target_width, target_height))
                if not out.isOpened():
                    print("❌ Fallback codec 'mp4v' also failed. Exiting.")
                    break

            start_time = time.time()
            start_time_utc = datetime.datetime.utcnow()
            while True:
                ret, frame = camera.read()
                if not ret:
                    print('❌ Error: Failed to capture frame')
                    break
                
                resized_frame = cv2.resize(frame, (target_width, target_height))
                
                results = model.track(resized_frame, persist=True)
                annotated_frame = results[0].plot()

                with frame_lock:
                    video_frame = resized_frame.copy()
                    yolo_frame = annotated_frame.copy()

                out.write(resized_frame)

                video_chunk_length = int(os.getenv("VIDEO_CHUNK_LENGTH_SEC", 60))
                if time.time() - start_time >= video_chunk_length:
                    out.release()
                    break

            print(f"💾 Video saved to {output_file}")
            
            def upload_detect_file(file_path, beesIn, beesOut, detectedBees):
                bee_counts_history.append({
                    "incoming": beesIn,
                    "outgoing": beesOut,
                    "detected": detectedBees,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                if beesIn > 0 or beesOut > 0:
                    print(f"☁️ Uploading debug file: {file_path}")
                    upload_file_async(file_path, start_time_utc)
                    upload_file_async(output_file, start_time_utc)
                else:
                    print("🤫 No bees detected, skipping upload")

            count_bees_async(output_file, output_video_path=debug_output_file, on_complete=upload_detect_file, detection_line_coefficient=detection_line_coefficient)
            delete_old_mp4_files()

    except KeyboardInterrupt:
        print("🛑 Recording and uploading stopped by user")

    finally:
        camera.release()

if __name__ == '__main__':
    observer_thread = threading.Thread(target=startObserverClient)
    observer_thread.daemon = True
    observer_thread.start()
    from waitress import serve
    print("🚀 --- Starting web server on http://0.0.0.0:3030 ---")
    serve(app, host="0.0.0.0", port=3030)
