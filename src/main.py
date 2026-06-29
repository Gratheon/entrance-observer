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
from scipy.spatial.distance import pdist, squareform

from src.cameras import list_available_cameras, get_default_camera_config, initialize_camera
from src.video_utils import VideoWriterFactory
from app_settings import (
    DEFAULT_CAMERA_PROPERTIES,
    DEFAULT_STORAGE_SETTINGS,
    get_night_mode_settings,
    get_telemetry_settings,
    get_video_settings,
    get_storage_settings,
    has_effective_api_token,
    load_raw_settings,
    merge_settings,
    save_settings_file,
)
from uploader import upload_file_async, delete_old_mp4_files
import storage_manager
from counter import count_bees_from_frames_async

# enable GPU acceleration
cv2.CAP_GSTREAMER

app = Flask(__name__)
video_frame = None
yolo_frame = None
frame_lock = threading.Lock()
bee_counts_history = deque(maxlen=3600)  # Store up to last 10h. 10*60*6 entries (1 hour if updated every 10 sec)
capture_thread_running = False
camera_properties = DEFAULT_CAMERA_PROPERTIES.copy()
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
    """Checks if the current time is within the configured processing hours."""
    night_mode = get_night_mode_settings()
    if not night_mode.get("enabled", True):
        return True

    day_start_hour = int(night_mode.get("day_start_hour", 6))
    day_end_hour = int(night_mode.get("day_end_hour", 22))

    if day_start_hour == day_end_hour:
        return True

    current_hour = datetime.datetime.now().hour
    if day_start_hour < day_end_hour:
        return day_start_hour <= current_hour < day_end_hour

    # Supports schedules crossing midnight, e.g. active from 22:00 to 06:00.
    return current_hour >= day_start_hour or current_hour < day_end_hour

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
   <!doctype html>
   <html lang="en">
     <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Entrance Observer</title>
       <link rel="preconnect" href="https://fonts.googleapis.com">
       <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
       <link href="https://fonts.googleapis.com/css?family=Open+Sans:300,400,700&subset=latin,cyrillic&display=swap" rel="stylesheet">
       <style>
         :root {
           --color-page: #ffffff;
           --color-menu: #f8f8f8;
           --color-muted: #ececec;
           --color-border: #c5c5c5;
           --color-text: #222222;
           --color-secondary: #555555;
           --color-accent: #0248ff;
           --color-warning: #ffd900;
           --shadow-card: 0 8px 24px rgba(0, 0, 0, 0.06);
         }

         * {
           box-sizing: border-box;
           font-family: 'Open Sans', sans-serif;
         }

         html,
         body {
           margin: 0;
           min-height: 100%;
           background: var(--color-page);
           color: var(--color-text);
         }

         body {
           min-height: 100vh;
         }

         a {
           color: inherit;
           text-decoration: none;
         }

         h1,
         h2,
         h3 {
           margin: 0;
           font-weight: 700;
         }

         p {
           margin: 0;
         }

         .app-shell {
           display: flex;
           min-height: 100vh;
         }

         .side-menu {
           flex: 0 0 220px;
           width: 220px;
           background: var(--color-menu);
           border-right: 1px solid var(--color-border);
           display: flex;
           flex-direction: column;
           padding: 18px 14px;
         }

         .menu-title {
           padding: 6px 10px 18px;
           border-bottom: 1px solid var(--color-border);
           margin-bottom: 12px;
         }

         .menu-title strong {
           display: block;
           font-size: 18px;
           line-height: 1.2;
         }

         .menu-title span {
           display: block;
           margin-top: 5px;
           color: var(--color-secondary);
           font-size: 12px;
         }

         .menu-section {
           display: flex;
           flex-direction: column;
           gap: 4px;
           list-style: none;
           margin: 0;
           padding: 0;
         }

         .menu-link {
           border: 1px solid transparent;
           border-radius: 8px;
           color: #555;
           display: flex;
           align-items: center;
           gap: 9px;
           padding: 10px;
           font-size: 14px;
           line-height: 1.2;
           transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
         }

         .menu-link:hover,
         .menu-link.active {
           background: #ffffff;
           border-color: var(--color-border);
           color: #000000;
         }

         .menu-link.active {
           font-weight: 700;
         }

         .menu-icon {
           display: inline-flex;
           align-items: center;
           justify-content: center;
           width: 20px;
           height: 20px;
           color: #8a8f98;
         }

         .menu-footer {
           margin-top: auto;
           padding: 18px 10px 0;
           color: var(--color-secondary);
           font-size: 12px;
           display: flex;
           flex-direction: column;
           gap: 8px;
         }

         .menu-footer a:hover {
           text-decoration: underline;
         }

         .main-column {
           flex: 1;
           min-width: 0;
           display: flex;
           flex-direction: column;
         }

         .top-bar {
           min-height: 76px;
           border-bottom: 1px solid var(--color-border);
           display: flex;
           align-items: center;
           justify-content: flex-start;
           gap: 24px;
           padding: 14px 28px;
           background: #ffffff;
         }

         .page-heading {
           display: flex;
           flex-direction: column;
           gap: 4px;
         }

         .page-heading h1 {
           font-size: 24px;
           line-height: 1.2;
         }

         .page-heading p {
           color: var(--color-secondary);
           font-size: 13px;
         }

         .brand-logo {
           display: flex;
           align-items: center;
           justify-content: center;
           flex-shrink: 0;
           padding: 0 10px 16px;
           margin-bottom: 6px;
         }

         .brand-logo img {
           display: block;
           width: 138px;
           max-width: 100%;
           height: auto;
         }

         .content {
           flex: 1;
           padding: 24px 28px 32px;
           background: #ffffff;
         }
         .content-section[hidden] {
           display: none;
         }

         .section-header {
           display: flex;
           align-items: flex-start;
           justify-content: space-between;
           gap: 16px;
           margin-bottom: 16px;
         }

         .section-header h2 {
           font-size: 20px;
         }

         .section-header p {
           color: var(--color-secondary);
           font-size: 13px;
           margin-top: 4px;
         }

         .card {
           background: #ffffff;
           border: 1px solid var(--color-border);
           border-radius: 10px;
           box-shadow: var(--shadow-card);
           padding: 18px;
         }

         .preview-card {
           display: flex;
           flex-direction: column;
           gap: 16px;
         }

         .preview-toolbar {
           display: flex;
           align-items: center;
           justify-content: space-between;
           gap: 12px;
           flex-wrap: wrap;
         }

         .toggle-label {
           display: inline-flex;
           align-items: center;
           gap: 8px;
           color: var(--color-secondary);
           font-size: 14px;
           cursor: pointer;
         }

         .toggle-label input {
           width: 16px;
           height: 16px;
         }

         .hint {
           color: var(--color-secondary);
           font-size: 12px;
         }

         .preview-stack {
           display: flex;
           flex-direction: column;
           align-items: center;
           gap: 12px;
         }

         #video-container {
           position: relative;
           display: inline-block;
           max-width: 100%;
           border-radius: 8px;
           overflow: hidden;
           background: #111;
           border: 1px solid var(--color-border);
         }

         #video-feed-img {
           display: block;
           max-width: 100%;
           height: auto;
         }

         #detection-line {
           position: absolute;
           left: 0;
           width: 100%;
           height: 4px;
           background: #ff2f2f;
           cursor: ns-resize;
           top: {{ detection_line_coefficient * 100 }}%;
           box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.55);
         }

         .entrance-label {
           width: 100%;
           text-align: center;
           padding: 10px 12px;
           border: 1px dashed var(--color-border);
           border-radius: 8px;
           color: #424242;
           cursor: pointer;
           font-size: 18px;
           font-weight: 700;
           background: var(--color-menu);
         }

         .controls-container {
           display: grid;
           grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
           gap: 12px;
         }

         .settings-group {
           display: flex;
           flex-direction: column;
           gap: 12px;
         }

         .settings-group h3 {
           color: #424242;
           font-size: 16px;
           margin-bottom: 2px;
         }

         .settings-form {
           display: grid;
           grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
           gap: 12px;
         }

         .settings-field {
           display: flex;
           flex-direction: column;
           gap: 6px;
           padding: 12px;
           border: 1px solid var(--color-border);
           border-radius: 8px;
           background: var(--color-menu);
         }

         .settings-field label {
           color: #424242;
           font-size: 13px;
           font-weight: 700;
         }

         .settings-field input[type='text'],
         .settings-field input[type='password'],
         .settings-field input[type='number'],
         .settings-field select {
           width: 100%;
           border: 1px solid var(--color-border);
           border-radius: 6px;
           padding: 9px 10px;
           background: #ffffff;
           color: var(--color-text);
           font-size: 14px;
         }

         .settings-field .hint {
           line-height: 1.35;
         }

         .settings-actions {
           display: flex;
           align-items: center;
           gap: 12px;
           flex-wrap: wrap;
         }

         .primary-button {
           border: 1px solid var(--color-accent);
           border-radius: 8px;
           background: var(--color-accent);
           color: #ffffff;
           cursor: pointer;
           font-weight: 700;
           padding: 10px 14px;
         }

         .save-status {
           color: var(--color-secondary);
           font-size: 13px;
         }

         .control {
           display: grid;
           grid-template-columns: 130px minmax(120px, 1fr) 48px;
           align-items: center;
           gap: 12px;
           padding: 12px;
           border: 1px solid var(--color-border);
           border-radius: 8px;
           background: var(--color-menu);
         }

         .control label {
           color: #424242;
           font-size: 13px;
           font-weight: 700;
         }

         .control input[type='range'] {
           width: 100%;
           accent-color: var(--color-accent);
         }

         .control span {
           color: var(--color-secondary);
           font-size: 13px;
           text-align: right;
           font-variant-numeric: tabular-nums;
         }

         .stats-grid {
           display: grid;
           grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
           gap: 12px;
           margin-bottom: 16px;
         }

         .metric-card {
           border: 1px solid var(--color-border);
           border-radius: 10px;
           padding: 14px;
           background: var(--color-menu);
         }

         .metric-card span {
           color: var(--color-secondary);
           display: block;
           font-size: 12px;
           margin-bottom: 6px;
         }

         .metric-card strong {
           display: block;
           font-size: 24px;
           line-height: 1.1;
           font-variant-numeric: tabular-nums;
         }

         .charts-grid {
           display: grid;
           grid-template-columns: 1fr;
           gap: 16px;
         }

         .chart-card h3,
         .table-card h3 {
           color: #424242;
           font-size: 16px;
           margin-bottom: 12px;
         }

         .chart-card canvas {
           width: 100% !important;
           max-height: 260px;
         }

         .table-wrapper {
           overflow-x: auto;
         }

         #bee-counts-table {
           width: 100%;
           min-width: 860px;
           border-collapse: collapse;
           font-size: 13px;
         }

         #bee-counts-table th,
         #bee-counts-table td {
           border-bottom: 1px solid #dddddd;
           padding: 9px 10px;
           text-align: left;
         }

         #bee-counts-table th {
           background: var(--color-menu);
           color: #424242;
           font-weight: 700;
         }

         #bee-counts-table td {
           font-variant-numeric: tabular-nums;
         }

         @media (min-width: 1200px) {
           .charts-grid {
             grid-template-columns: repeat(3, minmax(0, 1fr));
           }
         }

         @media (max-width: 760px) {
           .app-shell {
             flex-direction: column;
           }

           .side-menu {
             width: 100%;
             flex: 0 0 auto;
             border-right: none;
             border-bottom: 1px solid var(--color-border);
             padding: 12px;
           }

           .menu-title {
             padding: 4px 6px 10px;
             margin-bottom: 8px;
           }

           .menu-section {
             flex-direction: row;
             overflow-x: auto;
           }

           .menu-link {
             white-space: nowrap;
           }

           .menu-footer {
             display: none;
           }

           .top-bar,
           .content {
             padding-left: 16px;
             padding-right: 16px;
           }

           .top-bar {
             align-items: flex-start;
           }

           .page-heading h1 {
             font-size: 20px;
           }

           .brand-logo img {
             width: 110px;
           }

           .control {
             grid-template-columns: 1fr;
             gap: 8px;
           }

           .control span {
             text-align: left;
           }
         }
       </style>
     </head>
     <body>
       <div class="app-shell">
         <nav class="side-menu" aria-label="Entrance observer sections">
           <a class="brand-logo" href="https://app.gratheon.com/apiaries" target="_blank" rel="noreferrer" aria-label="Open Gratheon app">
             <img src="{{ url_for('send_img', path='gratheon.png') }}" alt="Gratheon Logo">
           </a>
           <div class="menu-title">
             <strong>Entrance Observer</strong>
             <span>Local device UI</span>
           </div>
           <ul class="menu-section">
             <li>
               <a class="menu-link active" href="#camera-preview" data-section-link="camera-preview">
                 <span class="menu-icon" aria-hidden="true">▣</span>
                 <span>Camera Preview</span>
               </a>
             </li>
             <li>
               <a class="menu-link" href="#settings" data-section-link="settings">
                 <span class="menu-icon" aria-hidden="true">⚙</span>
                 <span>Settings</span>
               </a>
             </li>
             <li>
               <a class="menu-link" href="#statistics" data-section-link="statistics">
                 <span class="menu-icon" aria-hidden="true">↗</span>
                 <span>Statistics</span>
               </a>
             </li>
           </ul>
           <div class="menu-footer">
             <a href="https://gratheon.com/docs/entrance-observer/" target="_blank" rel="noreferrer">Docs</a>
             <a href="https://gratheon.com/terms" target="_blank" rel="noreferrer">Terms of Use</a>
             <a href="https://gratheon.com/privacy" target="_blank" rel="noreferrer">Privacy policy</a>
           </div>
         </nav>

         <main class="main-column">
           <header class="top-bar">
            <div class="page-heading">
              <h1>Beehive entrance monitor</h1>
              <p>Camera stream, device settings, and live traffic metrics.</p>
            </div>
          </header>

           <div class="content">
             <section id="camera-preview" class="content-section" data-section="camera-preview">
               <div class="section-header">
                 <div>
                   <h2>Camera Preview</h2>
                   <p>Use the detection line and entrance marker to calibrate bee direction.</p>
                 </div>
               </div>

               <div class="card preview-card">
                 <div class="preview-toolbar">
                   <label class="toggle-label">
                     <input type="checkbox" id="feed-toggle">
                     Show Live Feed
                   </label>
                   <span class="hint">Drag the red line to change the counting boundary.</span>
                 </div>

                 <div class="preview-stack" id="preview-stack">
                   <div id="hive-entrance-label" class="entrance-label">&darr; Hive Entrance &darr;</div>
                   <div id="video-container">
                     <img id="video-feed-img" src="{{ url_for('video_feed_yolo') }}" alt="Camera stream with bee detection overlay">
                     <div id="detection-line" aria-label="Detection line"></div>
                   </div>
                 </div>
               </div>
             </section>

            <section id="settings" class="content-section" data-section="settings" hidden>
              <div class="section-header">
                <div>
                  <h2>Settings</h2>
                  <p>Device, telemetry, and night mode settings are persisted locally.</p>
                </div>
              </div>

              <div class="settings-group">
                <div class="card">
                  <h3>Telemetry</h3>
                  <div class="settings-form">
                    <div class="settings-field">
                      <label for="api_token">API token</label>
                      <input type="password" id="api_token" name="api_token" autocomplete="off" placeholder="{{ 'Configured' if api_token_configured else 'Paste token' }}">
                      <span class="hint">Leave blank to keep the current token. Stored locally in settings.</span>
                    </div>
                    <div class="settings-field">
                      <label for="hive_id">Hive ID</label>
                      <input type="text" id="hive_id" name="hive_id" value="{{ telemetry_settings.hive_id }}">
                    </div>
                    <div class="settings-field">
                      <label for="section_id">Section / box ID</label>
                      <input type="text" id="section_id" name="section_id" value="{{ telemetry_settings.section_id }}">
                    </div>
                    <div class="settings-field">
                      <label for="base_url">Telemetry base URL</label>
                      <input type="text" id="base_url" name="base_url" value="{{ telemetry_settings.base_url }}">
                    </div>
                    <div class="settings-field">
                      <label for="upload_path">Telemetry upload path</label>
                      <input type="text" id="upload_path" name="upload_path" value="{{ telemetry_settings.upload_path }}">
                    </div>
                    <div class="settings-field">
                      <label for="upload_url">Full telemetry upload URL override</label>
                      <input type="text" id="upload_url" name="upload_url" value="{{ telemetry_settings.upload_url }}" placeholder="Optional">
                    </div>
                    <div class="settings-field">
                      <label for="video_upload_url">Video upload GraphQL URL</label>
                      <input type="text" id="video_upload_url" name="video_upload_url" value="{{ telemetry_settings.video_upload_url }}">
                    </div>
                  </div>
                </div>

                <div class="card">
                  <h3>Night mode</h3>
                  <div class="settings-form">
                    <label class="settings-field toggle-label" for="night_mode_enabled">
                      <input type="checkbox" id="night_mode_enabled" name="enabled" {% if night_mode_settings.enabled %}checked{% endif %}>
                      Pause recording and AI processing at night
                    </label>
                    <div class="settings-field">
                      <label for="day_start_hour">Day starts at hour</label>
                      <input type="number" id="day_start_hour" name="day_start_hour" min="0" max="23" value="{{ night_mode_settings.day_start_hour }}">
                      <span class="hint">0-23, default 6.</span>
                    </div>
                    <div class="settings-field">
                      <label for="day_end_hour">Day ends at hour</label>
                      <input type="number" id="day_end_hour" name="day_end_hour" min="0" max="23" value="{{ night_mode_settings.day_end_hour }}">
                      <span class="hint">0-23, default 22. Set start and end equal to process all day.</span>
                    </div>
                  </div>
                </div>

                <div class="card">
                  <h3>Video capture and upload</h3>
                  <div class="settings-form">
                    <div class="settings-field">
                      <label for="video_fps">Requested camera FPS</label>
                      <input type="number" id="video_fps" min="1" max="120" value="{{ video_settings.fps }}">
                    </div>
                    <div class="settings-field">
                      <label for="width_px">Capture width</label>
                      <input type="number" id="width_px" min="160" max="3840" value="{{ video_settings.width_px }}">
                    </div>
                    <div class="settings-field">
                      <label for="height_px">Capture height</label>
                      <input type="number" id="height_px" min="120" max="2160" value="{{ video_settings.height_px }}">
                    </div>
                    <div class="settings-field">
                      <label for="detect_video_width">Detection upload width</label>
                      <input type="number" id="detect_video_width" min="160" max="3840" value="{{ video_settings.detect_video_width }}">
                      <span class="hint">Lower this when network upload bandwidth is limited.</span>
                    </div>
                    <div class="settings-field">
                      <label for="detect_video_height">Detection upload height</label>
                      <input type="number" id="detect_video_height" min="120" max="2160" value="{{ video_settings.detect_video_height }}">
                    </div>
                    <div class="settings-field">
                      <label for="video_chunk_length_sec">Video chunk length, seconds</label>
                      <input type="number" id="video_chunk_length_sec" min="5" max="600" value="{{ video_settings.video_chunk_length_sec }}">
                    </div>
                    <div class="settings-field">
                      <label for="upload_max_fps">Upload video FPS cap</label>
                      <input type="number" id="upload_max_fps" min="0" max="120" value="{{ video_settings.upload_max_fps }}">
                      <span class="hint">0 disables the cap. Lower values reduce uploaded detection video size.</span>
                    </div>
                    <label class="settings-field toggle-label" for="auto_calibrate_fps">
                      <input type="checkbox" id="auto_calibrate_fps" {% if video_settings.auto_calibrate_fps %}checked{% endif %}>
                      Auto-calibrate sustainable camera FPS
                    </label>
                    <label class="settings-field toggle-label" for="upload_videos_enabled">
                      <input type="checkbox" id="upload_videos_enabled" {% if video_settings.upload_videos_enabled %}checked{% endif %}>
                      Upload detection videos
                    </label>
                  </div>
                </div>

                <div class="card">
                  <h3>Storage and retention</h3>
                  <div class="settings-form">
                    <div class="settings-field">
                      <label for="videos_dir">Videos directory</label>
                      <input type="text" id="videos_dir" value="{{ storage_settings.videos_dir }}">
                    </div>
                    <div class="settings-field">
                      <label for="telemetry_dir">Telemetry directory</label>
                      <input type="text" id="telemetry_dir" value="{{ storage_settings.telemetry_dir }}">
                    </div>
                    <div class="settings-field">
                      <label for="runs_dir">Runs directory</label>
                      <input type="text" id="runs_dir" value="{{ storage_settings.runs_dir }}">
                    </div>
                    <div class="settings-field">
                      <label for="video_retention_minutes">Raw video retention, minutes</label>
                      <input type="number" id="video_retention_minutes" min="1" value="{{ storage_settings.video_retention_minutes }}">
                    </div>
                    <div class="settings-field">
                      <label for="detect_video_retention_minutes">Detection video retention, minutes</label>
                      <input type="number" id="detect_video_retention_minutes" min="1" value="{{ storage_settings.detect_video_retention_minutes }}">
                    </div>
                    <div class="settings-field">
                      <label for="telemetry_retention_days">Telemetry retention, days</label>
                      <input type="number" id="telemetry_retention_days" min="1" value="{{ storage_settings.telemetry_retention_days }}">
                    </div>
                    <div class="settings-field">
                      <label for="runs_retention_days">Runs retention, days</label>
                      <input type="number" id="runs_retention_days" min="1" value="{{ storage_settings.runs_retention_days }}">
                    </div>
                    <div class="settings-field">
                      <label for="min_free_disk_mb">Minimum free disk, MB</label>
                      <input type="number" id="min_free_disk_mb" min="0" value="{{ storage_settings.min_free_disk_mb }}">
                      <span class="hint">Old managed files are deleted until at least this much disk is free.</span>
                    </div>
                    <div class="settings-field">
                      <label for="max_managed_storage_mb">Max managed storage, MB</label>
                      <input type="number" id="max_managed_storage_mb" min="0" value="{{ storage_settings.max_managed_storage_mb }}">
                      <span class="hint">0 means unlimited; disk free guard still applies.</span>
                    </div>
                    <label class="settings-field toggle-label" for="delete_uploaded_videos">
                      <input type="checkbox" id="delete_uploaded_videos" {% if storage_settings.delete_uploaded_videos %}checked{% endif %}>
                      Delete local videos after successful upload
                    </label>
                  </div>
                </div>

                <div class="settings-actions">
                  <button type="button" class="primary-button" id="save-app-settings">Save app settings</button>
                  <span class="save-status" id="app-settings-status" role="status"></span>
                </div>

                <div class="card controls-container">
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
            </section>

             <section id="statistics" class="content-section" data-section="statistics" hidden>
               <div class="section-header">
                 <div>
                   <h2>Statistics</h2>
                   <p>Recent bee traffic, detection, speed, and interaction metrics.</p>
                 </div>
               </div>

               <div class="stats-grid" aria-label="Latest metrics">
                 <div class="metric-card">
                   <span>Incoming</span>
                   <strong id="metric-incoming">--</strong>
                 </div>
                 <div class="metric-card">
                   <span>Outgoing</span>
                   <strong id="metric-outgoing">--</strong>
                 </div>
                 <div class="metric-card">
                   <span>Net Flow</span>
                   <strong id="metric-net-flow">--</strong>
                 </div>
                 <div class="metric-card">
                   <span>Detected</span>
                   <strong id="metric-detected">--</strong>
                 </div>
               </div>

               <div class="charts-grid">
                 <div class="card chart-card">
                   <h3>Bee Traffic</h3>
                   <canvas id="traffic-chart" width="400" height="160"></canvas>
                 </div>
                 <div class="card chart-card">
                   <h3>Bee Detection</h3>
                   <canvas id="detection-chart" width="400" height="160"></canvas>
                 </div>
                 <div class="card chart-card">
                   <h3>Bee Speed</h3>
                   <canvas id="speed-chart" width="400" height="160"></canvas>
                 </div>
               </div>

               <div class="card table-card" style="margin-top: 16px;">
                 <h3>Recent measurements</h3>
                 <div class="table-wrapper">
                   <table id="bee-counts-table">
                     <thead>
                       <tr>
                         <th>Time</th>
                         <th>Incoming</th>
                         <th>Outgoing</th>
                         <th>Net Flow</th>
                         <th>Detected</th>
                         <th>Avg Speed</th>
                         <th>P95 Speed</th>
                         <th>Stationary</th>
                         <th>Interactions</th>
                       </tr>
                     </thead>
                     <tbody></tbody>
                   </table>
                 </div>
               </div>
             </section>
           </div>
         </main>
       </div>

       <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
       <script>
         const sections = Array.from(document.querySelectorAll('[data-section]'));
         const sectionLinks = Array.from(document.querySelectorAll('[data-section-link]'));

         function showSection(sectionId) {
           const targetSection = sections.find(section => section.dataset.section === sectionId) || sections[0];
           sections.forEach(section => {
             section.hidden = section !== targetSection;
           });
           sectionLinks.forEach(link => {
             const isActive = link.dataset.sectionLink === targetSection.dataset.section;
             link.classList.toggle('active', isActive);
             link.setAttribute('aria-current', isActive ? 'page' : 'false');
           });

          if (targetSection.dataset.section === 'statistics') {
            setTimeout(() => {
              if (typeof trafficChart !== 'undefined' && trafficChart) trafficChart.resize();
              if (typeof detectionChart !== 'undefined' && detectionChart) detectionChart.resize();
              if (typeof speedChart !== 'undefined' && speedChart) speedChart.resize();
            }, 0);
          }
         }

         sectionLinks.forEach(link => {
           link.addEventListener('click', (event) => {
             event.preventDefault();
             const sectionId = link.dataset.sectionLink;
             history.replaceState(null, '', `#${sectionId}`);
             showSection(sectionId);
           });
         });

         showSection((window.location.hash || '#camera-preview').slice(1));
       </script>
       <script>
         let trafficChart, detectionChart, speedChart;

         function formatNumber(value, digits = 0) {
           const number = Number(value);
           if (!Number.isFinite(number)) return '--';
           return number.toFixed(digits);
         }

         function updateMetric(id, value, digits = 0) {
           const element = document.getElementById(id);
           if (element) element.textContent = formatNumber(value, digits);
         }

         function fetchBeeCounts() {
           fetch('/api/bee_counts')
             .then(response => response.json())
             .then(data => {
               const tableBody = document.querySelector('#bee-counts-table tbody');
               tableBody.innerHTML = '';
               data.forEach(count => {
                 const row = document.createElement('tr');
                 row.innerHTML = `
                   <td>${count.time}</td>
                   <td>${formatNumber(count.bees_in)}</td>
                   <td>${formatNumber(count.bees_out)}</td>
                   <td>${formatNumber(count.net_flow)}</td>
                   <td>${formatNumber(count.detected_bees)}</td>
                   <td>${formatNumber(count.avg_speed_px_per_frame, 2)}</td>
                   <td>${formatNumber(count.p95_speed_px_per_frame, 2)}</td>
                   <td>${formatNumber(count.stationary_bees_count)}</td>
                   <td>${formatNumber(count.bee_interactions)}</td>
                 `;
                 tableBody.insertBefore(row, tableBody.firstChild);
               });

               const latest = data[data.length - 1] || {};
               updateMetric('metric-incoming', latest.bees_in);
               updateMetric('metric-outgoing', latest.bees_out);
               updateMetric('metric-net-flow', latest.net_flow);
               updateMetric('metric-detected', latest.detected_bees);

               const labels = data.map(d => d.time);

               const beesInData = data.map(d => d.bees_in);
               const beesOutData = data.map(d => d.bees_out);
               const netFlowData = data.map(d => d.net_flow);

               const detectedBeesData = data.map(d => d.detected_bees);
               const stationaryBeesData = data.map(d => d.stationary_bees_count);
               const interactionsData = data.map(d => d.bee_interactions);

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
                       datasets: datasets,
                     },
                     options: {
                       responsive: true,
                       maintainAspectRatio: false,
                       interaction: {
                         mode: 'index',
                         intersect: false,
                       },
                       plugins: {
                         legend: {
                           labels: {
                             boxWidth: 12,
                             font: { family: 'Open Sans' },
                           },
                         },
                       },
                       scales: {
                         y: {
                           beginAtZero: true,
                           grid: { color: '#ececec' },
                         },
                         x: {
                           grid: { display: false },
                         },
                       },
                     },
                   });
                 }
                 return chartInstance;
               }

               trafficChart = createOrUpdateChart(trafficChart, 'traffic-chart', labels, [
                 { label: 'Incoming Bees', data: beesInData, borderColor: 'rgb(75, 192, 192)', backgroundColor: 'rgba(75, 192, 192, 0.12)', tension: 0.1 },
                 { label: 'Outgoing Bees', data: beesOutData, borderColor: 'rgb(255, 99, 132)', backgroundColor: 'rgba(255, 99, 132, 0.12)', tension: 0.1 },
                 { label: 'Net Flow', data: netFlowData, borderColor: 'rgb(54, 162, 235)', backgroundColor: 'rgba(54, 162, 235, 0.12)', tension: 0.1 },
               ]);

               detectionChart = createOrUpdateChart(detectionChart, 'detection-chart', labels, [
                 { label: 'Detected Bees', data: detectedBeesData, borderColor: 'rgb(255, 206, 86)', backgroundColor: 'rgba(255, 206, 86, 0.12)', tension: 0.1 },
                 { label: 'Stationary Bees', data: stationaryBeesData, borderColor: 'rgb(153, 102, 255)', backgroundColor: 'rgba(153, 102, 255, 0.12)', tension: 0.1 },
                 { label: 'Interactions', data: interactionsData, borderColor: 'rgb(255, 99, 132)', backgroundColor: 'rgba(255, 99, 132, 0.12)', tension: 0.1 },
               ]);

               speedChart = createOrUpdateChart(speedChart, 'speed-chart', labels, [
                 { label: 'Avg Speed (px/frame)', data: avgSpeedData, borderColor: 'rgb(255, 159, 64)', backgroundColor: 'rgba(255, 159, 64, 0.12)', tension: 0.1 },
                 { label: 'P95 Speed (px/frame)', data: p95SpeedData, borderColor: 'rgb(75, 192, 75)', backgroundColor: 'rgba(75, 192, 75, 0.12)', tension: 0.1 },
               ]);
             });
         }
         setInterval(fetchBeeCounts, 10000);
         fetchBeeCounts();
       </script>
       <script>
         const hiveEntranceLabel = document.getElementById('hive-entrance-label');
         const previewStack = document.getElementById('preview-stack');
         const videoContainer = document.getElementById('video-container');
         let entrancePosition = '{{ entrance_position }}';

         function renderEntrancePosition() {
           if (entrancePosition === 'top') {
             hiveEntranceLabel.innerHTML = '&uarr; Hive Entrance &uarr;';
             previewStack.insertBefore(hiveEntranceLabel, videoContainer);
           } else {
             hiveEntranceLabel.innerHTML = '&darr; Hive Entrance &darr;';
             previewStack.insertBefore(hiveEntranceLabel, videoContainer.nextSibling);
           }
         }

         renderEntrancePosition();

         hiveEntranceLabel.addEventListener('click', () => {
           entrancePosition = entrancePosition === 'bottom' ? 'top' : 'bottom';
           renderEntrancePosition();
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
           videoFeedImg.src = feedToggle.checked ? liveFeedUrl : yoloFeedUrl;
         });
       </script>
       <script>
         const detectionLine = document.getElementById('detection-line');
         let isDragging = false;

         detectionLine.addEventListener('mousedown', () => {
           isDragging = true;
         });

         videoContainer.addEventListener('mousemove', (event) => {
           if (!isDragging) return;
           const rect = videoContainer.getBoundingClientRect();
           const y = event.clientY - rect.top;
           const height = rect.height;
           let coefficient = y / height;
           if (coefficient < 0) coefficient = 0;
           if (coefficient > 1) coefficient = 1;
           detectionLine.style.top = `${coefficient * 100}%`;
         });

         document.addEventListener('mouseup', (event) => {
           if (!isDragging) return;
           isDragging = false;
           const rect = videoContainer.getBoundingClientRect();
           const y = event.clientY - rect.top;
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
         });

         const saveAppSettingsButton = document.getElementById('save-app-settings');
         const appSettingsStatus = document.getElementById('app-settings-status');

         saveAppSettingsButton.addEventListener('click', () => {
           const numberValue = (id) => Number(document.getElementById(id).value);
           const apiToken = document.getElementById('api_token').value;
           const telemetry = {
             hive_id: document.getElementById('hive_id').value,
             section_id: document.getElementById('section_id').value,
             base_url: document.getElementById('base_url').value,
             upload_path: document.getElementById('upload_path').value,
             upload_url: document.getElementById('upload_url').value,
             video_upload_url: document.getElementById('video_upload_url').value,
           };
           if (apiToken) {
             telemetry.api_token = apiToken;
           }

           fetch('/api/settings', {
             method: 'POST',
             headers: {
               'Content-Type': 'application/json',
             },
             body: JSON.stringify({
               telemetry,
               night_mode: {
                 enabled: document.getElementById('night_mode_enabled').checked,
                 day_start_hour: numberValue('day_start_hour'),
                 day_end_hour: numberValue('day_end_hour'),
               },
               video: {
                 fps: numberValue('video_fps'),
                 width_px: numberValue('width_px'),
                 height_px: numberValue('height_px'),
                 detect_video_width: numberValue('detect_video_width'),
                 detect_video_height: numberValue('detect_video_height'),
                 video_chunk_length_sec: numberValue('video_chunk_length_sec'),
                 upload_max_fps: numberValue('upload_max_fps'),
                 auto_calibrate_fps: document.getElementById('auto_calibrate_fps').checked,
                 upload_videos_enabled: document.getElementById('upload_videos_enabled').checked,
               },
               storage: {
                 videos_dir: document.getElementById('videos_dir').value,
                 telemetry_dir: document.getElementById('telemetry_dir').value,
                 runs_dir: document.getElementById('runs_dir').value,
                 video_retention_minutes: numberValue('video_retention_minutes'),
                 detect_video_retention_minutes: numberValue('detect_video_retention_minutes'),
                 telemetry_retention_days: numberValue('telemetry_retention_days'),
                 runs_retention_days: numberValue('runs_retention_days'),
                 min_free_disk_mb: numberValue('min_free_disk_mb'),
                 max_managed_storage_mb: numberValue('max_managed_storage_mb'),
                 delete_uploaded_videos: document.getElementById('delete_uploaded_videos').checked,
               },
             }),
           })
             .then(response => response.json())
             .then(data => {
               if (!data.success) throw new Error(data.error || 'Failed to save settings');
               document.getElementById('api_token').value = '';
               document.getElementById('api_token').placeholder = 'Configured';
               appSettingsStatus.textContent = 'Saved';
             })
             .catch(error => {
               appSettingsStatus.textContent = error.message;
             });
         });

         const controls = document.querySelectorAll('.control input[type="range"]');
         controls.forEach(control => {
           control.addEventListener('input', (event) => {
             const valueSpan = document.getElementById(`${event.target.id}-value`);
             valueSpan.textContent = event.target.value;
           });
           control.addEventListener('change', (event) => {
             const property = event.target.name;
             const value = event.target.value;
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
     </body>
   </html>
   """
    raw_settings = load_raw_settings()
    telemetry_settings = get_telemetry_settings(raw_settings)
    night_mode_settings = get_night_mode_settings(raw_settings)
    video_settings = get_video_settings(raw_settings)
    storage_settings = get_storage_settings(raw_settings)
    return render_template_string(
        html,
        detection_line_coefficient=detection_line_coefficient,
        camera_properties=camera_properties,
        entrance_position=entrance_position,
        telemetry_settings=telemetry_settings,
        night_mode_settings=night_mode_settings,
        video_settings=video_settings,
        storage_settings=storage_settings,
        api_token_configured=has_effective_api_token(raw_settings),
    )

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
@app.route("/api/settings", methods=['POST'])
def set_app_settings():
    data = request.get_json() or {}
    raw_settings = load_raw_settings()
    settings = merge_settings(raw_settings)

    telemetry_payload = data.get("telemetry", {})
    if isinstance(telemetry_payload, dict):
        allowed_telemetry_keys = {
            "api_token",
            "hive_id",
            "section_id",
            "base_url",
            "upload_path",
            "upload_url",
            "dir",
            "video_upload_url",
        }
        for key, value in telemetry_payload.items():
            if key not in allowed_telemetry_keys:
                continue
            if key == "api_token" and value == "":
                continue
            settings["telemetry"][key] = str(value).strip()

    night_mode_payload = data.get("night_mode", {})
    if isinstance(night_mode_payload, dict):
        if "enabled" in night_mode_payload:
            settings["night_mode"]["enabled"] = bool(night_mode_payload["enabled"])
        for key in ("day_start_hour", "day_end_hour"):
            if key not in night_mode_payload:
                continue
            try:
                hour = int(night_mode_payload[key])
            except (TypeError, ValueError):
                return jsonify(success=False, error=f"{key} must be an integer from 0 to 23"), 400
            if hour < 0 or hour > 23:
                return jsonify(success=False, error=f"{key} must be from 0 to 23"), 400
            settings["night_mode"][key] = hour

    video_payload = data.get("video", {})
    if isinstance(video_payload, dict):
        allowed_video_ints = {
            "fps": (1, 120),
            "width_px": (160, 3840),
            "height_px": (120, 2160),
            "detect_video_width": (160, 3840),
            "detect_video_height": (120, 2160),
            "video_chunk_length_sec": (5, 600),
            "upload_max_fps": (0, 120),
        }
        for key, (min_value, max_value) in allowed_video_ints.items():
            if key not in video_payload:
                continue
            try:
                value = int(video_payload[key])
            except (TypeError, ValueError):
                return jsonify(success=False, error=f"{key} must be an integer"), 400
            if value < min_value or value > max_value:
                return jsonify(success=False, error=f"{key} must be from {min_value} to {max_value}"), 400
            settings["video"][key] = value
        for key in ("auto_calibrate_fps", "upload_videos_enabled"):
            if key in video_payload:
                settings["video"][key] = bool(video_payload[key])

    storage_payload = data.get("storage", {})
    if isinstance(storage_payload, dict):
        allowed_storage_text = {"videos_dir", "telemetry_dir", "runs_dir"}
        for key in allowed_storage_text:
            if key in storage_payload:
                settings["storage"][key] = str(storage_payload[key]).strip() or DEFAULT_STORAGE_SETTINGS[key]

        allowed_storage_ints = {
            "video_retention_minutes": 1,
            "detect_video_retention_minutes": 1,
            "telemetry_retention_days": 1,
            "runs_retention_days": 1,
            "min_free_disk_mb": 0,
            "max_managed_storage_mb": 0,
        }
        for key, min_value in allowed_storage_ints.items():
            if key not in storage_payload:
                continue
            try:
                value = int(storage_payload[key])
            except (TypeError, ValueError):
                return jsonify(success=False, error=f"{key} must be an integer"), 400
            if value < min_value:
                return jsonify(success=False, error=f"{key} must be at least {min_value}"), 400
            settings["storage"][key] = value
        if "delete_uploaded_videos" in storage_payload:
            settings["storage"]["delete_uploaded_videos"] = bool(storage_payload["delete_uploaded_videos"])
    save_settings_file(settings)
    load_settings()
    storage_manager.cleanup_storage()
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
            time.sleep(1)
            continue

        timestamp = int(datetime.datetime.now().timestamp())
        videos_dir = get_storage_settings().get("videos_dir", "./videos")
        os.makedirs(videos_dir, exist_ok=True)
        output_file = os.path.join(videos_dir, f'{timestamp}.mp4')

        out = VideoWriterFactory.create_writer(output_file, writer_fps, (target_width, target_height))
        if not out:
            break

        video_chunk_length = int(get_video_settings().get("video_chunk_length_sec", 20))
        
        print(f"🎥 Recording a {video_chunk_length} second video at a target of {writer_fps:.2f} FPS...")

        start_time = time.monotonic()
        frames_written = 0
        total_write_time = 0
        aborted_for_night = False
        while (time.monotonic() - start_time) < video_chunk_length:
            if not is_day_time():
                print("🌙 Night mode enabled during recording, stopping current video chunk.")
                aborted_for_night = True
                while not video_queue.empty():
                    try:
                        video_queue.get_nowait()
                    except queue.Empty:
                        break
                break
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
        if aborted_for_night:
            try:
                os.remove(output_file)
            except OSError:
                pass
            continue

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
            time.sleep(1)
            continue

        timestamp = int(datetime.datetime.now().timestamp())
        videos_dir = get_storage_settings().get("videos_dir", "./videos")
        os.makedirs(videos_dir, exist_ok=True)
        detections_video_file = os.path.join(videos_dir, f'{timestamp}_detect.mp4')

        video_chunk_length = int(get_video_settings().get("video_chunk_length_sec", 20))
        
        # We'll process as many frames as we can in the chunk duration
        frames_for_counting = []
        total_inference_time = 0
        frames_processed = 0
        total_interactions = 0
        aborted_for_night = False
        start_time = time.time()
        while (time.time() - start_time) < video_chunk_length:
            if not is_day_time():
                print("🌙 Night mode enabled during AI processing, stopping current detection chunk.")
                aborted_for_night = True
                break
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

            # Interaction detection
            boxes = results[0].boxes
            if boxes.is_track and len(boxes.xyxy) > 1:
                coords = np.array([((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) for box in boxes.xyxy.cpu()])
                dist_matrix = squareform(pdist(coords))
                close_pairs = np.argwhere((dist_matrix > 0) & (dist_matrix < 40)) # 40px threshold
                
                for i, j in close_pairs:
                    if i < j:
                        total_interactions += 1
                        x1, y1 = coords[i]
                        x2, y2 = coords[j]
                        cv2.circle(annotated_frame, (int(x1), int(y1)), 5, (0, 255, 255), -1)
                        cv2.circle(annotated_frame, (int(x2), int(y2)), 5, (0, 255, 255), -1)
                        cv2.line(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)

            # Draw the tracking lines
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

        if aborted_for_night or not frames_for_counting:
            if aborted_for_night:
                print("🌙 Detection chunk discarded because night mode is active.")
            else:
                print("⚠️ No frames processed in this detection chunk; skipping telemetry.")
            continue

        actual_duration = time.time() - start_time
        avg_inference_time = total_inference_time / frames_processed if frames_processed > 0 else 0
        print(f"🧠 Avg inference time (last chunk): {avg_inference_time:.4f}s")

        start_time_utc = datetime.datetime.utcnow()

        def upload_detect_file(file_path, metrics_data):
            metrics_data["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bee_counts_history.append(metrics_data)
            
            if metrics_data["bees_in"] > 0 or metrics_data["bees_out"] > 0 or metrics_data["detected_bees"] > 0:
                print(f"☁️ Uploading debug file: {file_path}")
                # The original `output_file` is not available in this thread.
                # We pass the detections file path for both arguments to prevent a crash.
                upload_file_async(file_path, file_path, start_time_utc)
            else:
                print("🤫 No detections in this chunk, skipping upload")

        detect_video_fps = len(frames_for_counting) / actual_duration if actual_duration > 0 else writer_fps
        video_settings = get_video_settings()
        upload_max_fps = int(video_settings.get("upload_max_fps", 0) or 0)
        output_video_fps = detect_video_fps
        video_frame_stride = 1
        if upload_max_fps > 0 and detect_video_fps > upload_max_fps:
            video_frame_stride = max(1, round(detect_video_fps / upload_max_fps))
            output_video_fps = detect_video_fps / video_frame_stride
        print(f"📹 Writing detections video with {output_video_fps:.2f} FPS (source {detect_video_fps:.2f} FPS, stride {video_frame_stride})")
        detections_video_writer = VideoWriterFactory.create_writer(detections_video_file, output_video_fps, (detect_video_width, detect_video_height))
        
        count_bees_from_frames_async(frames_for_counting, total_interactions, output_video_path=detections_video_file, on_complete=upload_detect_file, detection_line_coefficient=detection_line_coefficient, video_writer=detections_video_writer, writer_fps=output_video_fps, frame_shape=(detect_video_height, detect_video_width), entrance_position=entrance_position, video_frame_stride=video_frame_stride)
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
    video_settings = get_video_settings()
    storage_manager.ensure_managed_directories()
    storage_manager.cleanup_storage()

    FPS = int(video_settings.get("fps", 30))
    WIDTH_PX = int(video_settings.get("width_px", 640))
    HEIGHT_PX = int(video_settings.get("height_px", 480))
    DETECT_VIDEO_WIDTH = int(video_settings.get("detect_video_width", 320))
    DETECT_VIDEO_HEIGHT = int(video_settings.get("detect_video_height", 240))

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

    if video_settings.get("auto_calibrate_fps", True):
        # Calibrate at the target resolution to get the true sustainable FPS.
        writer_fps = measure_actual_fps(camera, target_width, target_height)
        if writer_fps < 1:
            print(f"⚠️ FPS calibration failed. Falling back to requested FPS: {FPS}")
            writer_fps = FPS
    else:
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
    raw_settings = load_raw_settings()
    settings = merge_settings(raw_settings)
    settings["camera_properties"] = camera_properties
    settings["detection_line_coefficient"] = detection_line_coefficient
    settings["entrance_position"] = entrance_position
    save_settings_file(settings)

def load_settings():
    global camera_properties, detection_line_coefficient, entrance_position
    raw_settings = load_raw_settings()
    settings = merge_settings(raw_settings)
    camera_properties.update(settings.get("camera_properties", camera_properties))
    detection_line_coefficient = settings.get("detection_line_coefficient", detection_line_coefficient)
    entrance_position = settings.get("entrance_position", entrance_position)

    if not raw_settings:
        save_settings()

if __name__ == '__main__':
    observer_thread = threading.Thread(target=startObserverClient)
    observer_thread.daemon = True
    observer_thread.start()
    from waitress import serve
    print("🚀 --- Starting web server on http://0.0.0.0:3030 ---")
    serve(app, host="0.0.0.0", port=3030)
