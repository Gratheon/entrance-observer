import os
import threading
import requests
import cv2
import json

from ultralytics import YOLO, solutions
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


model = YOLO("best.pt")


def count_bees_async(relativeFilePath):
    # Define a function to upload the file asynchronously
    upload_thread = threading.Thread(target=countBees, args=(relativeFilePath,))
    upload_thread.start()


def countBeesAndReportTelemetry(relativeFilePath):
    beesIn, beesOut = countBees(relativeFilePath)

    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("BOX_ID")

    # Make multipart/form-data request
    response = requests.post(
        'https://telemetry.gratheon.com/entrance/v1/movement',
        headers={
            'Authorization': f'Bearer {bearer_token}'
        },
        data={
            "boxId": boxId,
            "hiveId": hiveId,
            "beesIn": beesIn,
            "beesOut": beesOut,
        },
        timeout=120,
        allow_redirects=True
    )

    if response.status_code == 200:
        print("Video uploaded successfully")
    else:
        print("Error uploading video:", response.status_code)

    print(response.text)


def countBees(relativeFilePath):
    cap = cv2.VideoCapture(relativeFilePath)
    assert cap.isOpened(), "Error reading video file"
    w, h, fps = (
        int(cap.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )

    # Define region points
    region_points = [(0, round(h / 2)), (round(w), round(h / 2))]

    # Video writer
    # video_writer = cv2.VideoWriter(
    #     "object_counting_output.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
    # )

    # Init Object Counter
    counter = solutions.ObjectCounter(
        view_img=True,
        reg_pts=region_points,
        names=model.names,
        draw_tracks=True,
        line_thickness=2,
    )

    while cap.isOpened():
        success, im0 = cap.read()
        if not success:
            print(
                "Video frame is empty or video processing has been successfully completed."
            )
            break
        tracks = model.track(im0, persist=True, show=False)

        im0 = counter.start_counting(im0, tracks)
        # video_writer.write(im0)

    cap.release()
    # video_writer.release()
    cv2.destroyAllWindows()

    # print("counter: ", counter.in_counts)
    # print("counter: ", counter.out_counts)

    return counter.in_counts, counter.out_counts