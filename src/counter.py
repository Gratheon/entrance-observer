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


def count_bees_async(relativeFilePath, display_video=False, output_video_path=None):
    print(f"Starting bee counting for {relativeFilePath}", flush=True)
    # This function is kept for compatibility, but the new approach is to call countBees and report_telemetry_async separately
    if display_video:
        print("Warning: display_video=True in async mode might not work as expected. Run countBees in the main thread for UI.", flush=True)
    upload_thread = threading.Thread(target=countBeesAndReportTelemetry, args=(relativeFilePath, display_video, output_video_path))
    upload_thread.start()

def report_telemetry_async(beesIn, beesOut):
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry_async(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)


def countBeesAndReportTelemetry(relativeFilePath, display_video=False, output_video_path=None):
    start_time = time.time()  # Record the start time

    try:
        beesIn, beesOut = countBees(relativeFilePath, display_video, output_video_path)
        print(f"Bee counting completed: {beesIn} in, {beesOut} out", flush=True)
    except Exception as e:
        print(f"Error during bee counting: {e}", flush=True)
        return
    
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")
    base_url = os.getenv("TELEMETRY_BASE_URL", "https://telemetry.gratheon.com")
    telemetry.report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)
    
    end_time = time.time()  # Record the end time
    print(f"Time taken for countBeesAndReportTelemetry: {end_time - start_time:.2f} seconds", flush=True)


from collections import defaultdict

track_history = defaultdict(list)

def countBees(relativeFilePath, display_video=False, output_video_path=None):
    track_history.clear()
    if not os.path.exists(relativeFilePath):
        raise FileNotFoundError(f"Video file not found at path: {relativeFilePath}")
    cap = cv2.VideoCapture(relativeFilePath)
    assert cap.isOpened(), f"Error reading video file: {relativeFilePath}"
    w, h, fps = (
        int(cap.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )

    out = None
    if output_video_path:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))

    # Define counting line
    line_y = round(h / 2)
    
    in_counts = 0
    out_counts = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.", flush=True)
            break

        results = model.track(frame, persist=True)

        if results[0].boxes.is_track:
            boxes = results[0].boxes.xyxy.cpu()
            track_ids = results[0].boxes.id.int().cpu().tolist()

            annotator = Annotator(frame, line_width=2)

            for box, track_id in zip(boxes, track_ids):
                annotator.box_label(box, str(track_id), color=(0, 200, 0))
                bbox_center = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

                track = track_history[track_id]
                track.append((float(bbox_center[0]), float(bbox_center[1])))
                if len(track) > 2:
                    # Check if the bee crossed the line
                    if track[-2][1] < line_y and track[-1][1] >= line_y:
                        in_counts += 1
                    elif track[-2][1] > line_y and track[-1][1] <= line_y:
                        out_counts += 1
                
                if len(track) > 30:
                    track.pop(0)

        # Draw the counting line
        cv2.line(frame, (0, line_y), (w, line_y), (200, 0, 0), 2)
        
        # Display counts on the frame
        cv2.putText(frame, f"In: {in_counts}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 200), 2)
        cv2.putText(frame, f"Out: {out_counts}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 200), 2)

        if display_video:
            cv2.imshow("Bee Counter", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        
        if out:
            out.write(frame)
        
        streamer.video_frame = frame

    cap.release()
    if out:
        out.release()
        print(f"Debug video saved to {output_video_path}", flush=True)
    if display_video:
        cv2.destroyAllWindows()

    print(f"Counting results: {in_counts} in, {out_counts} out", flush=True)
    
    return in_counts, out_counts
