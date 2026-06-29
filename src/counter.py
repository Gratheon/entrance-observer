import os
import threading
import cv2
import time
import numpy as np
import app_settings
import telemetry
import metrics
from ultralytics import YOLO
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

weights_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'weights', 'best.pt'))
model = YOLO(weights_path)
track_history = defaultdict(list)

def count_bees_from_frames_async(frames, total_interactions, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    print(f"🐝 Starting bee counting for a batch of {len(frames)} frames", flush=True)
    upload_thread = threading.Thread(target=countBeesAndReportTelemetry, args=(frames, total_interactions, output_video_path, on_complete, detection_line_coefficient, video_writer, writer_fps, frame_shape, entrance_position))
    upload_thread.start()

def report_telemetry_async(metrics_data):
    telemetry_settings = app_settings.get_telemetry_settings()
    telemetry.report_telemetry_async(
        metrics_data,
        telemetry_settings.get("api_token"),
        telemetry_settings.get("hive_id"),
        telemetry_settings.get("section_id"),
        telemetry_settings.get("base_url"),
        telemetry_settings=telemetry_settings,
    )

def countBeesAndReportTelemetry(frames, total_interactions, output_video_path=None, on_complete=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    start_time = time.time()

    try:
        beesIn, beesOut, detectedBees, final_track_history = countBees(frames, output_video_path, detection_line_coefficient, video_writer, writer_fps, frame_shape, entrance_position)
        print(f"✅ Bee counting completed: {beesIn} in, {beesOut} out, {detectedBees} detected", flush=True)
    except Exception as e:
        print(f"❌ Error during bee counting: {e}", flush=True)
        return
    finally:
        if video_writer:
            video_writer.release()
    
    metrics_data = {
        "bees_in": beesIn,
        "bees_out": beesOut,
        "detected_bees": detectedBees,
        "bee_interactions": total_interactions
    }
    
    derived_metrics = metrics.calculate_derived_metrics(final_track_history)
    metrics_data.update(derived_metrics)
    metrics_data["net_flow"] = beesIn - beesOut
    
    telemetry.save_track_history_locally(final_track_history, frame_shape)
    
    telemetry_settings = app_settings.get_telemetry_settings()
    telemetry.report_telemetry(
        metrics_data,
        telemetry_settings.get("api_token"),
        telemetry_settings.get("hive_id"),
        telemetry_settings.get("section_id"),
        telemetry_settings.get("base_url"),
        telemetry_settings=telemetry_settings,
    )
    
    if on_complete:
        on_complete(output_video_path, metrics_data)

    end_time = time.time()
    print(f"⏱️ Time taken for countBeesAndReportTelemetry: {end_time - start_time:.2f} seconds", flush=True)

def countBees(frames, output_video_path=None, detection_line_coefficient=None, video_writer=None, writer_fps=None, frame_shape=None, entrance_position='bottom'):
    track_history.clear()
    
    # It's important to operate on a copy of track_history for each run
    # to avoid issues with concurrent processing.
    local_track_history = defaultdict(list)

    if not frames:
        return 0, 0, 0, local_track_history

    if frame_shape is not None:
        writer_h, writer_w = frame_shape
    else:
        writer_h, writer_w = frames[0][0].shape[:2]
    
    if detection_line_coefficient is None:
        detection_line_coefficient = float(os.getenv("DETECTION_LINE", 0.5))
    line_y_writer = round(writer_h * detection_line_coefficient)
    effective_fps = writer_fps if writer_fps and writer_fps > 0 else float(os.getenv("FPS", 30))

    video_chunk_length = float(os.getenv("VIDEO_CHUNK_LENGTH_SEC", 30))

    in_counts = 0
    out_counts = 0
    detected_bees = set()

    close_video_writer = False
    if output_video_path and not video_writer:
        close_video_writer = True
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        video_writer = cv2.VideoWriter(output_video_path, fourcc, effective_fps, (writer_w, writer_h))
        if not video_writer.isOpened():
            print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_video_path, fourcc, effective_fps, (writer_w, writer_h))
            if not video_writer.isOpened():
                print("❌ Fallback codec 'mp4v' also failed. No debug video will be saved.")
                video_writer = None

    for i, (frame, results, capture_time) in enumerate(frames):
        # Counting line must use the same coordinate space as model detections.
        line_y_counting = round(frame.shape[0] * detection_line_coefficient)

        if video_writer:
            resized_annotated_frame = cv2.resize(frame, (writer_w, writer_h))
            cv2.line(resized_annotated_frame, (0, line_y_writer), (writer_w, line_y_writer), (0, 0, 255), 2)
            video_writer.write(resized_annotated_frame)

        boxes = results[0].boxes
        if boxes.is_track:
            for box, track_id in zip(boxes.xyxy.cpu(), boxes.id.int().cpu().tolist()):
                detected_bees.add(track_id)
                bbox_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                track = local_track_history[track_id]
                track.append((float(bbox_center[0]), float(bbox_center[1])))
                if len(track) >= 2:
                    if entrance_position == 'bottom':
                        if track[-2][1] < line_y_counting and track[-1][1] >= line_y_counting:
                            in_counts += 1
                        elif track[-2][1] > line_y_counting and track[-1][1] <= line_y_counting:
                            out_counts += 1
                    else: # entrance_position == 'top'
                        if track[-2][1] < line_y_counting and track[-1][1] >= line_y_counting:
                            out_counts += 1
                        elif track[-2][1] > line_y_counting and track[-1][1] <= line_y_counting:
                            in_counts += 1
                if len(track) > video_chunk_length * effective_fps:  # Keep history for the length of the video chunk
                    track.pop(0)

    if video_writer and close_video_writer:
        video_writer.release()

    print(f"📊 Counting results: {in_counts} in, {out_counts} out", flush=True)
    
    return in_counts, out_counts, len(detected_bees), local_track_history
