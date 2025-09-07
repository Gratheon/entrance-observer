import os
import time
import datetime
import cv2
import platform
import json
from flask import Flask, Response, render_template_string, jsonify, request
import threading
import logging
from ultralytics import YOLO
from collections import deque, defaultdict
import queue
import numpy as np
import random

from src.cameras import list_available_cameras, get_default_camera_config, initialize_camera
from src.video_utils import VideoWriterFactory
from uploader import upload_file_async, delete_old_mp4_files
from counter import count_bees_from_frames_async

# enable GPU acceleration
cv2.CAP_GSTREAMER

app = Flask(__name__)
video_frame = None
yolo_frame = None
frame_lock = threading.Lock()
bee_counts_history = deque(maxlen=3600)  # Store up to last 10h. 10*60*6 entries (1 hour if updated every 10 sec)
capture_thread_running = False
camera_properties = {
    "brightness": 40,
    "contrast": 4,
    "saturation": 70,
    "gain": 0,
    "exposure": -6,
    "white_balance_temperature": 4000,
    "gamma": 78,
    "sharpness": 128,
    "backlight": 1
}
camera_lock = threading.Lock()
camera_instance = None
detection_line_coefficient = 0.5
entrance_position = 'bottom'
track_history = defaultdict(list)
track_colors = {}


weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','weights', 'best.pt'))
logging.getLogger('ultralytics').setLevel(logging.WARNING)
model = YOLO(weights_path)

def is_day_time():
    """
    Checks if the current time is within the configured day hours.
    Night mode is disabled if DAY_START_HOUR and DAY_END_HOUR are the same.
    """
    day_start_hour = int(os.getenv("DAY_START_HOUR", 6))
    day_end_hour = int(os.getenv("DAY_END_HOUR", 22))

    if day_start_hour == day_end_hour:
        return True

    current_hour = datetime.datetime.now().hour
    return day_start_hour <= current_hour < day_end_hour

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
         .controls-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 20px;
            background-color: white;
            border: 1px solid #c5c5c5;
            border-radius: 5px;
         }
         .control {
            display: flex;
            justify-content: space-between;
            align-items: center;
         }
         .control label {
            margin-right: 10px;
         }
         .control input {
            width: 200px;
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
            <div class="controls-container">
                <h2>Camera Settings</h2>
                <div class="control">
                    <label for="brightness">Brightness</label>
                    <input type="range" id="brightness" name="brightness" min="0" max="255" value="{{ camera_properties.brightness }}">
                    <span id="brightness-value">{{ camera_properties.brightness }}</span>
                </div>
                <div class="control">
                    <label for="contrast">Contrast</label>
                    <input type="range" id="contrast" name="contrast" min="0" max="255" value="{{ camera_properties.contrast }}">
                    <span id="contrast-value">{{ camera_properties.contrast }}</span>
                </div>
                <div class="control">
                    <label for="saturation">Saturation</label>
                    <input type="range" id="saturation" name="saturation" min="0" max="255" value="{{ camera_properties.saturation }}">
                    <span id="saturation-value">{{ camera_properties.saturation }}</span>
                </div>
                <div class="control">
                    <label for="gain">Gain</label>
                    <input type="range" id="gain" name="gain" min="0" max="255" value="{{ camera_properties.gain }}">
                    <span id="gain-value">{{ camera_properties.gain }}</span>
                </div>
                <div class="control">
                    <label for="exposure">Exposure</label>
                    <input type="range" id="exposure" name="exposure" min="-10" max="0" value="{{ camera_properties.exposure }}">
                    <span id="exposure-value">{{ camera_properties.exposure }}</span>
                </div>
                <div class="control">
                    <label for="white_balance_temperature">White Balance</label>
                    <input type="range" id="white_balance_temperature" name="white_balance_temperature" min="2000" max="6500" value="{{ camera_properties.white_balance_temperature }}">
                    <span id="white_balance_temperature-value">{{ camera_properties.white_balance_temperature }}</span>
                </div>
                <div class="control">
                    <label for="gamma">Gamma</label>
                    <input type="range" id="gamma" name="gamma" min="1" max="500" value="{{ camera_properties.gamma }}">
                    <span id="gamma-value">{{ camera_properties.gamma }}</span>
                </div>
                <div class="control">
                    <label for="sharpness">Sharpness</label>
                    <input type="range" id="sharpness" name="sharpness" min="0" max="255" value="{{ camera_properties.sharpness }}">
                    <span id="sharpness-value">{{ camera_properties.sharpness }}</span>
                </div>
                <div class="control">
                    <label for="backlight">Backlight Comp</label>
                    <input type="range" id="backlight" name="backlight" min="0" max="2" value="{{ camera_properties.backlight }}">
                    <span id="backlight-value">{{ camera_properties.backlight }}</span>
                </div>
            </div>
         </div>
         <div id="hive-entrance-label" style="text-align: center; padding-top: 20px; font-size: 24px; color: #424242; cursor: pointer;">
           &darr; Hive Entrance &darr;
         </div>
         <div id="bee-counts-container" style="padding: 20px;">
           <h3 style="text-align: center; color: #424242; font-weight: 500;">Bee Traffic</h3>
           <canvas id="traffic-chart" width="400" height="100"></canvas>
           <h3 style="text-align: center; color: #424242; font-weight: 500;">Bee Detection</h3>
           <canvas id="detection-chart" width="400" height="100"></canvas>
           <h3 style="text-align: center; color: #424242; font-weight: 500;">Bee Speed</h3>
           <canvas id="speed-chart" width="400" height="100"></canvas>
           <table id="bee-counts-table" style="width: 100%; border-collapse: collapse; margin-top: 20px;">
             <thead>
               <tr>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Time</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Incoming</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Outgoing</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Net Flow</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Detected</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Avg Speed</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">P95 Speed</th>
                 <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Stationary</th>
               </tr>
             </thead>
             <tbody>
             </tbody>
           </table>
         </div>
       </div>
       <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
       <script>
         let trafficChart, detectionChart, speedChart;
         function fetchBeeCounts() {
           fetch('/api/bee_counts')
             .then(response => response.json())
             .then(data => {
               const tableBody = document.querySelector('#bee-counts-table tbody');
               tableBody.innerHTML = '';
               data.forEach(count => {
                 const row = document.createElement('tr');
                 row.innerHTML = `
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.time}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.bees_in}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.bees_out}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.net_flow}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.detected_bees}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.avg_speed_px_per_frame.toFixed(2)}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.p95_speed_px_per_frame.toFixed(2)}</td>
                   <td style="border: 1px solid #ddd; padding: 8px;">${count.stationary_bees_count}</td>
                 `;
                 tableBody.insertBefore(row, tableBody.firstChild);
               });

               const labels = data.map(d => d.time);
               
               // Data for Traffic Chart
               const beesInData = data.map(d => d.bees_in);
               const beesOutData = data.map(d => d.bees_out);
               const netFlowData = data.map(d => d.net_flow);

               // Data for Detection Chart
               const detectedBeesData = data.map(d => d.detected_bees);
               const stationaryBeesData = data.map(d => d.stationary_bees_count);

               // Data for Speed Chart
               const avgSpeedData = data.map(d => d.avg_speed_px_per_frame);
               const p95SpeedData = data.map(d => d.p95_speed_px_per_frame);

               function createOrUpdateChart(chartInstance, chartId, chartLabels, datasets) {
                   if (chartInstance) {
                       chartInstance.data.labels = chartLabels;
                       datasets.forEach((dataset, index) => {
                           chartInstance.data.datasets[index].data = dataset.data;
                       });
                       chartInstance.update();
                   } else {
                       const ctx = document.getElementById(chartId).getContext('2d');
                       chartInstance = new Chart(ctx, {
                           type: 'line',
                           data: {
                               labels: chartLabels,
                               datasets: datasets
                           },
                           options: {
                               scales: {
                                   y: {
                                       beginAtZero: true
                                   }
                               }
                           }
                       });
                   }
                   return chartInstance;
               }

               trafficChart = createOrUpdateChart(trafficChart, 'traffic-chart', labels, [
                   { label: 'Incoming Bees', data: beesInData, borderColor: 'rgb(75, 192, 192)', tension: 0.1 },
                   { label: 'Outgoing Bees', data: beesOutData, borderColor: 'rgb(255, 99, 132)', tension: 0.1 },
                   { label: 'Net Flow', data: netFlowData, borderColor: 'rgb(54, 162, 235)', tension: 0.1 }
               ]);

               detectionChart = createOrUpdateChart(detectionChart, 'detection-chart', labels, [
                   { label: 'Detected Bees', data: detectedBeesData, borderColor: 'rgb(255, 206, 86)', tension: 0.1 },
                   { label: 'Stationary Bees', data: stationaryBeesData, borderColor: 'rgb(153, 102, 255)', tension: 0.1 }
               ]);

               speedChart = createOrUpdateChart(speedChart, 'speed-chart', labels, [
                   { label: 'Avg Speed (px/frame)', data: avgSpeedData, borderColor: 'rgb(255, 159, 64)', tension: 0.1 },
                   { label: 'P95 Speed (px/frame)', data: p95SpeedData, borderColor: 'rgb(75, 192, 75)', tension: 0.1 }
               ]);
             });
         }
         setInterval(fetchBeeCounts, 10000);
         fetchBeeCounts();
       </script>
       <script>
         const hiveEntranceLabel = document.getElementById('hive-entrance-label');
         let entrancePosition = '{{ entrance_position }}';

         if (entrancePosition === 'top') {
             hiveEntranceLabel.innerHTML = '&uarr; Hive Entrance &uarr;';
             document.querySelector('.container').insertBefore(hiveEntranceLabel, document.querySelector('.video-container'));
         } else {
             hiveEntranceLabel.innerHTML = '&darr; Hive Entrance &darr;';
         }

         hiveEntranceLabel.addEventListener('click', () => {
           if (entrancePosition === 'bottom') {
             entrancePosition = 'top';
             hiveEntranceLabel.innerHTML = '&uarr; Hive Entrance &uarr;';
             document.querySelector('.container').insertBefore(hiveEntranceLabel, document.querySelector('.video-container'));
           } else {
             entrancePosition = 'bottom';
             hiveEntranceLabel.innerHTML = '&darr; Hive Entrance &darr;';
             document.querySelector('.container').insertBefore(hiveEntranceLabel, document.getElementById('bee-counts-container'));
           }
           fetch('/api/set_entrance_position', {
             method: 'POST',
             headers: {
               'Content-Type': 'application/json',
             },
             body: JSON.stringify({ position: entrancePosition }),
           });
         });
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

         const controls = document.querySelectorAll('.control input');
         controls.forEach(control => {
             control.addEventListener('input', (e) => {
                 const valueSpan = document.getElementById(`${e.target.id}-value`);
                 valueSpan.textContent = e.target.value;
             });
             control.addEventListener('change', (e) => {
                 const property = e.target.name;
                 const value = e.target.value;
                 fetch('/api/set_camera_properties', {
                     method: 'POST',
                     headers: {
                         'Content-Type': 'application/json',
                     },
                     body: JSON.stringify({ [property]: value }),
                 });
             });
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
    return render_template_string(html, detection_line_coefficient=detection_line_coefficient, camera_properties=camera_properties, entrance_position=entrance_position)

@app.route("/api/set_camera_properties", methods=['POST'])
def set_camera_properties():
    global camera_properties, camera_instance
    data = request.get_json()
    with camera_lock:
        for key, value in data.items():
            if key in camera_properties:
                camera_properties[key] = int(value)
        if camera_instance:
            # This function will be created in cameras.py
            from src.cameras import apply_camera_properties
            apply_camera_properties(camera_instance, camera_properties)
    save_settings()
    return jsonify(success=True)

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

@app.route("/api/set_entrance_position", methods=['POST'])
def set_entrance_position():
    global entrance_position
    data = request.get_json()
    entrance_position = data['position']
    save_settings()
    return jsonify(success=True)

@app.route("/api/set_detection_line", methods=['POST'])
def set_detection_line():
    global detection_line_coefficient
    data = request.get_json()
    detection_line_coefficient = data['coefficient']
    save_settings()
    return jsonify(success=True)

def frame_capture_thread(camera, video_queue, ai_queue):
    """Optimized frame capture thread with better performance."""
    global capture_thread_running
    print("🚀 Starting frame capture thread...")
    frame_count = 0
    total_read_time = 0
    failed_reads = 0
    
    while capture_thread_running:
        start_read_time = time.monotonic()
        ret, frame = camera.read()
        read_duration = time.monotonic() - start_read_time
        total_read_time += read_duration
        frame_count += 1

        if frame_count % 100 == 0:
            avg_read_time = total_read_time / 100
            print(f"📸 Avg frame read time (last 100 frames): {avg_read_time:.4f}s")
            if failed_reads > 0:
                print(f"⚠️ Failed reads in last 100 frames: {failed_reads}")
                failed_reads = 0
            total_read_time = 0

        if ret and frame is not None:
            capture_time = time.monotonic()
            
            # Try to put frame in video queue (non-blocking)
            try:
                video_queue.put((frame.copy(), capture_time), block=False)
            except queue.Full:
                # Drop oldest frame and add new one
                try:
                    video_queue.get_nowait()
                    video_queue.put((frame.copy(), capture_time), block=False)
                except queue.Empty:
                    pass
            
            # Try to put frame in AI queue (non-blocking)
            try:
                ai_queue.put((frame.copy(), capture_time), block=False)
            except queue.Full:
                # Drop oldest frame and add new one
                try:
                    ai_queue.get_nowait()
                    ai_queue.put((frame.copy(), capture_time), block=False)
                except queue.Empty:
                    pass
        else:
            failed_reads += 1
            # If reading fails, wait a very short time before trying again
            time.sleep(0.001)
            
    print("🛑 Stopping frame capture thread...")

def video_writer_thread(video_queue, writer_fps, target_width, target_height):
    while capture_thread_running:
        if not is_day_time():
            print("🌙 Night time, skipping video recording. Waiting for day time...")
            while not video_queue.empty():
                try:
                    video_queue.get_nowait()
                except queue.Empty:
                    break
            time.sleep(60)
            continue

        timestamp = int(datetime.datetime.now().timestamp())
        output_file = f'./videos/{timestamp}.mp4'

        out = VideoWriterFactory.create_writer(output_file, writer_fps, (target_width, target_height))
        if not out:
            break

        video_chunk_length = int(os.getenv("VIDEO_CHUNK_LENGTH_SEC", 20))
        
        print(f"🎥 Recording a {video_chunk_length} second video at a target of {writer_fps:.2f} FPS...")

        start_time = time.monotonic()
        frames_written = 0
        total_write_time = 0
        while (time.monotonic() - start_time) < video_chunk_length:
            try:
                # Use a short timeout to remain responsive to the capture_thread_running flag
                frame, capture_time = video_queue.get(timeout=1)
                resized_frame = cv2.resize(frame, (target_width, target_height))
                
                start_write_time = time.monotonic()
                out.write(resized_frame)
                write_duration = time.monotonic() - start_write_time
                total_write_time += write_duration

                frames_written += 1
            except queue.Empty:
                # If the queue is empty, just continue the loop until the time is up
                if not capture_thread_running:
                    break
                continue
        
        out.release()
        actual_duration = time.monotonic() - start_time
        avg_write_time = total_write_time / frames_written if frames_written > 0 else 0
        print(f"💾 Video saved to {output_file} ({frames_written} frames, {actual_duration:.2f}s duration, avg write time: {avg_write_time:.4f}s)")

def processing_thread(ai_queue, writer_fps, target_width, target_height, detect_video_width, detect_video_height):
    global video_frame, yolo_frame
    while capture_thread_running:
        if not is_day_time():
            print("🌙 Night time, skipping AI processing. Waiting for day time...")
            try:
                frame, _ = ai_queue.get(timeout=1)
                overlay_text = "Processing paused during night time"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1
                font_thickness = 2
                text_size = cv2.getTextSize(overlay_text, font, font_scale, font_thickness)[0]
                text_x = (frame.shape[1] - text_size[0]) // 2
                text_y = (frame.shape[0] + text_size[1]) // 2
                cv2.putText(frame, overlay_text, (text_x, text_y), font, font_scale, (0, 0, 255), font_thickness)
                
                with frame_lock:
                    video_frame = frame.copy()
                    yolo_frame = frame.copy()
            except queue.Empty:
                pass
            time.sleep(60)
            continue

        timestamp = int(datetime.datetime.now().timestamp())
        detections_video_file = f'./videos/{timestamp}_detect.mp4'

        video_chunk_length = int(os.getenv("VIDEO_CHUNK_LENGTH_SEC", 20))
        
        # We'll process as many frames as we can in the chunk duration
        frames_for_counting = []
        total_inference_time = 0
        frames_processed = 0
        start_time = time.time()
        while (time.time() - start_time) < video_chunk_length:
            try:
                frame, capture_time = ai_queue.get(timeout=1)
            except queue.Empty:
                # If the queue is empty, we can wait a bit for new frames
                continue
            
            start_inference_time = time.monotonic()
            results = model.track(frame, persist=True)
            inference_duration = time.monotonic() - start_inference_time
            total_inference_time += inference_duration
            frames_processed += 1

            annotated_frame = results[0].plot()

            # Draw the tracking lines
            boxes = results[0].boxes
            if boxes.is_track:
                for box, track_id in zip(boxes.xyxy.cpu(), boxes.id.int().cpu().tolist()):
                    bbox_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    track = track_history[track_id]
                    track.append((float(bbox_center[0]), float(bbox_center[1])))
                    if len(track) > 30:
                        track.pop(0)

                    if track_id not in track_colors:
                        track_colors[track_id] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

                    if len(track) > 1:
                        track_np = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
                        cv2.polylines(annotated_frame, [track_np], isClosed=False, color=track_colors[track_id], thickness=2)

            with frame_lock:
                video_frame = frame.copy()
                yolo_frame = annotated_frame.copy()

            frames_for_counting.append((annotated_frame, results, capture_time))

        actual_duration = time.time() - start_time
        avg_inference_time = total_inference_time / frames_processed if frames_processed > 0 else 0
        print(f"🧠 Avg inference time (last chunk): {avg_inference_time:.4f}s")

        start_time_utc = datetime.datetime.utcnow()

        def upload_detect_file(file_path, metrics_data):
            metrics_data["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bee_counts_history.append(metrics_data)
            
            if metrics_data["bees_in"] > 0 or metrics_data["bees_out"] > 0:
                print(f"☁️ Uploading debug file: {file_path}")
                # The original `output_file` is not available in this thread.
                # We pass the detections file path for both arguments to prevent a crash.
                upload_file_async(file_path, file_path, start_time_utc)
            else:
                print("🤫 No bees detected, skipping upload")

        detect_video_fps = len(frames_for_counting) / actual_duration if actual_duration > 0 else writer_fps
        print(f"📹 Writing detections video with {detect_video_fps:.2f} FPS")
        detections_video_writer = VideoWriterFactory.create_writer(detections_video_file, detect_video_fps, (detect_video_width, detect_video_height))
        
        count_bees_from_frames_async(frames_for_counting, output_video_path=detections_video_file, on_complete=upload_detect_file, detection_line_coefficient=detection_line_coefficient, video_writer=detections_video_writer, writer_fps=detect_video_fps, frame_shape=(detect_video_height, detect_video_width), entrance_position=entrance_position)
        delete_old_mp4_files()

def warm_up_camera(camera, num_frames=10):
    """Reads and discards a number of frames to allow camera to stabilize."""
    print("📷 Warming up camera...")
    for _ in range(num_frames):
        ret, _ = camera.read()
        if not ret:
            print("⚠️ Could not read from camera during warmup.")
            return False
    print("✅ Camera warm-up successful.")
    return True

def measure_actual_fps(camera, target_width, target_height, duration_sec=5):
    """Measures the actual frames per second of the camera."""
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
    
    calib_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    calib_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Calibrating camera FPS over {duration_sec} seconds at {calib_width}x{calib_height} resolution...")
    
    if not warm_up_camera(camera):
        return 0

    frame_count = 0
    start_time = time.time()
    while (time.time() - start_time) < duration_sec:
        ret, _ = camera.read()
        if not ret:
            break
        frame_count += 1
    
    end_time = time.time()
    actual_duration = end_time - start_time
    if actual_duration == 0:
        print("⚠️ Calibration failed: duration was zero.")
        return 0
    
    fps = frame_count / actual_duration
    print(f"✅ Calibration successful: {fps:.2f} FPS")
    return fps

def startObserverClient():
    global capture_thread_running, camera_instance
    load_settings()
    FPS = int(os.getenv("FPS", 30))
    WIDTH_PX = int(os.getenv("WIDTH_PX", 640))
    HEIGHT_PX = int(os.getenv("HEIGHT_PX", 480))
    DETECT_VIDEO_WIDTH = int(os.getenv("DETECT_VIDEO_WIDTH", 320))
    DETECT_VIDEO_HEIGHT = int(os.getenv("DETECT_VIDEO_HEIGHT", 240))

    print(f"🖥️ Running on {platform.system()}")
    available_cameras = list_available_cameras()
    print(f"📷 Available cameras: {available_cameras}")

    camera_config = get_default_camera_config()
    device = camera_config["device"]
    backend = camera_config["backend"]
    
    if available_cameras and device not in available_cameras:
        device = available_cameras[0]
        print(f"⚠️ Default camera not available, using: {device}")

    target_width = WIDTH_PX
    target_height = HEIGHT_PX
    
    with camera_lock:
        camera_instance = initialize_camera(device, backend, target_width, target_height, FPS, camera_properties)
        camera = camera_instance

    if not camera.isOpened():
        print(f"❌ Failed to open any camera.")
        return
    
    print(f"🎯 Using resolution: {target_width}x{target_height}")

    # Calibrate at the target resolution to get the true sustainable FPS
    writer_fps = measure_actual_fps(camera, target_width, target_height)
    if writer_fps < 1:
        print(f"⚠️ FPS calibration failed. Falling back to requested FPS: {FPS}")
        writer_fps = FPS

    # Optimize queue sizes for better performance and lower memory usage
    # Use smaller queues to reduce latency and memory consumption
    video_queue = queue.Queue(maxsize=max(10, int(writer_fps * 1.5)))
    ai_queue = queue.Queue(maxsize=max(10, int(writer_fps * 1.5)))

    capture_thread_running = True
    cap_thread = threading.Thread(target=frame_capture_thread, args=(camera, video_queue, ai_queue))
    cap_thread.daemon = True
    cap_thread.start()

    writer_thread = threading.Thread(target=video_writer_thread, args=(video_queue, writer_fps, target_width, target_height))
    writer_thread.daemon = True
    writer_thread.start()

    proc_thread = threading.Thread(target=processing_thread, args=(ai_queue, writer_fps, target_width, target_height, DETECT_VIDEO_WIDTH, DETECT_VIDEO_HEIGHT))
    proc_thread.daemon = True
    proc_thread.start()

    try:
        while cap_thread.is_alive() and writer_thread.is_alive() and proc_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Recording and uploading stopped by user")
    finally:
        print("Cleaning up resources...")
        capture_thread_running = False
        if 'cap_thread' in locals() and cap_thread.is_alive():
            cap_thread.join()
        if 'writer_thread' in locals() and writer_thread.is_alive():
            writer_thread.join()
        if 'proc_thread' in locals() and proc_thread.is_alive():
            proc_thread.join()
        camera.release()

def save_settings():
    settings = {
        "camera_properties": camera_properties,
        "detection_line_coefficient": detection_line_coefficient,
        "entrance_position": entrance_position
    }
    settings_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(settings_dir, exist_ok=True)
    settings_path = os.path.join(settings_dir, 'settings.json')
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=4)

def load_settings():
    global camera_properties, detection_line_coefficient, entrance_position
    try:
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'settings.json')
        with open(settings_path, 'r') as f:
            settings = json.load(f)
            camera_properties.update(settings.get("camera_properties", camera_properties))
            detection_line_coefficient = settings.get("detection_line_coefficient", detection_line_coefficient)
            entrance_position = settings.get("entrance_position", entrance_position)
    except FileNotFoundError:
        save_settings()

if __name__ == '__main__':
    observer_thread = threading.Thread(target=startObserverClient)
    observer_thread.daemon = True
    observer_thread.start()
    from waitress import serve
    print("🚀 --- Starting web server on http://0.0.0.0:3030 ---")
    serve(app, host="0.0.0.0", port=3030)
