import os
import threading
import cv2
import time
import telemetry
from ultralytics import YOLO
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'weights', 'best.pt'))
model = YOLO(weights_path)
track_history = defaultdict(list)

def count_bees_from_frames_async(frames, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    print(f"🐝 Starting bee counting for a batch of {len(frames)} frames", flush=True)
    upload_thread = threading.Thread(target=countBeesAndReportTelemetry, args=(frames, output_video_path, on_complete, detection_line_coefficient, video_writer, writer_fps, frame_shape, entrance_position))
    upload_thread.start()

def report_telemetry_async(beesIn, beesOut):
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry_async(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)

def countBeesAndReportTelemetry(frames, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    start_time = time.time()

    try:
        beesIn, beesOut, detectedBees = countBees(frames, output_video_path, detection_line_coefficient, video_writer, writer_fps, frame_shape, entrance_position)
        print(f"✅ Bee counting completed: {beesIn} in, {beesOut} out, {detectedBees} detected", flush=True)
    except Exception as e:
        print(f"❌ Error during bee counting: {e}", flush=True)
        return
    finally:
        if video_writer:
            video_writer.release()
    
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)
    
    if on_complete:
        on_complete(output_video_path, beesIn, beesOut, detectedBees)

    end_time = time.time()
    print(f"⏱️ Time taken for countBeesAndReportTelemetry: {end_time - start_time:.2f} seconds", flush=True)

def countBees(frames, output_video_path=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    track_history.clear()
    
    h, w = frame_shape
    
    if detection_line_coefficient is None:
        detection_line_coefficient = float(os.getenv("DETECTION_LINE", 0.5))
    line_y = round(h * detection_line_coefficient)

    in_counts = 0
    out_counts = 0
    detected_bees = set()

    close_video_writer = False
    if output_video_path and not video_writer:
        close_video_writer = True
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        video_writer = cv2.VideoWriter(output_video_path, fourcc, writer_fps, (w, h))
        if not video_writer.isOpened():
            print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_video_path, fourcc, writer_fps, (w, h))
            if not video_writer.isOpened():
                print("❌ Fallback codec 'mp4v' also failed. No debug video will be saved.")
                video_writer = None

    for i, (frame, results, capture_time) in enumerate(frames):
        if video_writer:
            annotated_frame = results[0].plot()
            resized_annotated_frame = cv2.resize(annotated_frame, (w, h))
            video_writer.write(resized_annotated_frame)

        boxes = results[0].boxes
        if boxes.is_track:
            for box, track_id in zip(boxes.xyxy.cpu(), boxes.id.int().cpu().tolist()):
                detected_bees.add(track_id)
                bbox_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                track = track_history[track_id]
                track.append((float(bbox_center[0]), float(bbox_center[1])))
                if len(track) > 2:
                    if entrance_position == 'bottom':
                        if track[-2][1] < line_y and track[-1][1] >= line_y:
                            in_counts += 1
                        elif track[-2][1] > line_y and track[-1][1] <= line_y:
                            out_counts += 1
                    else: # entrance_position == 'top'
                        if track[-2][1] < line_y and track[-1][1] >= line_y:
                            out_counts += 1
                        elif track[-2][1] > line_y and track[-1][1] <= line_y:
                            in_counts += 1
                if len(track) > 30:
                    track.pop(0)

    if video_writer and close_video_writer:
        video_writer.release()

    print(f"📊 Counting results: {in_counts} in, {out_counts} out", flush=True)
    
    return in_counts, out_counts, len(detected_bees)
