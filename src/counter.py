import os
import threading
import cv2
import time
import streamer
import telemetry

from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','weights', 'best.pt'))

model = YOLO(weights_path)


def count_bees_async(relativeFilePath, display_video=False, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None):
    print(f"🐝 Starting bee counting for {relativeFilePath}", flush=True)
    # This function is kept for compatibility, but the new approach is to call countBees and report_telemetry_async separately
    if display_video:
        print("Warning: display_video=True in async mode might not work as expected. Run countBees in the main thread for UI.", flush=True)
    upload_thread = threading.Thread(target=countBeesAndReportTelemetry, args=(relativeFilePath, display_video, output_video_path, on_complete, detection_line_coefficient, video_writer))
    upload_thread.start()

def report_telemetry_async(beesIn, beesOut):
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry_async(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)


def countBeesAndReportTelemetry(relativeFilePath, display_video=False, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None):
    start_time = time.time()  # Record the start time

    try:
        beesIn, beesOut, detectedBees = countBees(relativeFilePath, display_video, output_video_path, detection_line_coefficient, video_writer)
        print(f"✅ Bee counting completed: {beesIn} in, {beesOut} out, {detectedBees} detected", flush=True)
    except Exception as e:
        print(f"❌ Error during bee counting: {e}", flush=True)
        return
    
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)
    
    if on_complete:
        on_complete(output_video_path, beesIn, beesOut, detectedBees)

    end_time = time.time()  # Record the end time
    print(f"⏱️ Time taken for countBeesAndReportTelemetry: {end_time - start_time:.2f} seconds", flush=True)


from collections import defaultdict

track_history = defaultdict(list)

def countBees(relativeFilePath, display_video=False, output_video_path=None, detection_line_coefficient=None, video_writer=None):
    track_history.clear()
    if not os.path.exists(relativeFilePath):
        raise FileNotFoundError(f"Video file not found at path: {relativeFilePath}")
    
    # Define counting line
    cap = cv2.VideoCapture(relativeFilePath)
    assert cap.isOpened(), f"Error reading video file: {relativeFilePath}"
    w, h, fps = (
        int(cap.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )
    if detection_line_coefficient is None:
        detection_line_coefficient = float(os.getenv("DETECTION_LINE", 0.5))
    line_y = round(h * detection_line_coefficient)
    cap.release()

    in_counts = 0
    out_counts = 0
    detected_bees = set()

    # Stream processing
    confidence = float(os.getenv("CONFIDENCE", 0.5))
    results = model.track(relativeFilePath, show=display_video, stream=True, persist=True, imgsz=w, conf=confidence)

    close_video_writer = False
    if output_video_path and not video_writer:
        close_video_writer = True
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))
        if not video_writer.isOpened():
            print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))
            if not video_writer.isOpened():
                print("❌ Fallback codec 'mp4v' also failed. No debug video will be saved.")
                video_writer = None

    for r in results:
        if video_writer:
            annotated_frame = r.plot()
            video_writer.write(annotated_frame)

        boxes = r.boxes
        if boxes.is_track:
            for box, track_id in zip(boxes.xyxy.cpu(), boxes.id.int().cpu().tolist()):
                detected_bees.add(track_id)
                bbox_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                track = track_history[track_id]
                track.append((float(bbox_center[0]), float(bbox_center[1])))
                if len(track) > 2:
                    if track[-2][1] < line_y and track[-1][1] >= line_y:
                        in_counts += 1
                    elif track[-2][1] > line_y and track[-1][1] <= line_y:
                        out_counts += 1
                if len(track) > 30:
                    track.pop(0)

    if video_writer and close_video_writer:
        video_writer.release()

    print(f"📊 Counting results: {in_counts} in, {out_counts} out", flush=True)
    
    return in_counts, out_counts, len(detected_bees)
