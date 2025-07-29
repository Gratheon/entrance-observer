import os
import threading
import requests
import cv2
import json
import time
import streamer

from ultralytics import YOLO, solutions
from ultralytics.utils.plotting import Annotator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


model = YOLO("best.pt")


def count_bees_async(relativeFilePath, display_video=False):
    # This function is kept for compatibility, but the new approach is to call countBees and report_telemetry_async separately
    if display_video:
        print("Warning: display_video=True in async mode might not work as expected. Run countBees in the main thread for UI.")
    upload_thread = threading.Thread(target=countBeesAndReportTelemetry, args=(relativeFilePath, display_video))
    upload_thread.start()

def report_telemetry_async(beesIn, beesOut):
    telemetry_thread = threading.Thread(target=report_telemetry, args=(beesIn, beesOut))
    telemetry_thread.start()

def report_telemetry(beesIn, beesOut):
    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")

    # Check if required environment variables are set
    if not bearer_token or not boxId:
        print("Error: Please set the API_TOKEN and SECTION_ID environment variables.")
        print("Skipping telemetry upload for testing purposes.")
        return

    # Prepare the payload
    payload = {
        "boxId": boxId,
        "hiveId": hiveId,
        "beesIn": beesIn,
        "beesOut": beesOut,
    }

    # Print the payload
    print("Payload to be sent:", payload)

    try:
        # Make multipart/form-data request
        response = requests.post(
            # 'http://localhost:8600/entrance/v1/movement',
            'https://telemetry.gratheon.com/entrance/v1/movement',
            headers={
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            },
            json=payload,  # Use json parameter instead of data
            timeout=120,
            allow_redirects=True
        )

        if response.status_code == 200:
            print("Counts reported successfully")
        else:
            print("Error reporting counts:", response.status_code)

        print(response.text)
    except Exception as e:
        print(f"Error sending telemetry: {e}")


def countBeesAndReportTelemetry(relativeFilePath, display_video=False):
    start_time = time.time()  # Record the start time

    try:
        beesIn, beesOut = countBees(relativeFilePath, display_video)
        print(f"Bee counting completed: {beesIn} in, {beesOut} out")
    except Exception as e:
        print(f"Error during bee counting: {e}")
        return
    
    report_telemetry(beesIn, beesOut)
    
    end_time = time.time()  # Record the end time
    print(f"Time taken for countBeesAndReportTelemetry: {end_time - start_time:.2f} seconds")


from collections import defaultdict

track_history = defaultdict(list)

def countBees(relativeFilePath, display_video=False):
    cap = cv2.VideoCapture(relativeFilePath)
    assert cap.isOpened(), "Error reading video file"
    w, h, fps = (
        int(cap.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )

    # Define counting line
    line_y = round(h / 2)
    
    in_counts = 0
    out_counts = 0

    model = YOLO("best.pt")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.")
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
        
        streamer.video_frame = frame

    cap.release()
    if display_video:
        cv2.destroyAllWindows()

    print(f"Counting results: {in_counts} in, {out_counts} out")
    
    return in_counts, out_counts
