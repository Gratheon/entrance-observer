import os
import cv2
import threading
import numpy as np
import datetime
import time
from uploader import upload_file_async, delete_old_mp4_files

class CSI_Camera:

    def __init__(self):
        # Initialize instance variables
        # OpenCV video capture element
        self.video_capture = None
        # The last captured image from the camera
        self.frame = None
        self.grabbed = False
        # The thread where the video capture runs
        self.read_thread = None
        self.read_lock = threading.Lock()
        self.running = False

    def open(self, gstreamer_pipeline_string):
        try:
            self.video_capture = cv2.VideoCapture(
                gstreamer_pipeline_string, cv2.CAP_GSTREAMER
            )
            # Grab the first frame to start the video capturing
            self.grabbed, self.frame = self.video_capture.read()

        except RuntimeError:
            self.video_capture = None
            print("Unable to open camera")
            print("Pipeline: " + gstreamer_pipeline_string)


    def start(self):
        if self.running:
            print('Video capturing is already running')
            return None
        # create a thread to read the camera image
        if self.video_capture != None:
            self.running = True
            self.read_thread = threading.Thread(target=self.updateCamera)
            self.read_thread.start()
        return self

    def stop(self):
        self.running = False
        # Kill the thread
        self.read_thread.join()
        self.read_thread = None

    def updateCamera(self):
        # This is the thread to read images from the camera
        while self.running:
            try:
                grabbed, frame = self.video_capture.read()
                with self.read_lock:
                    self.grabbed = grabbed
                    self.frame = frame
            except RuntimeError:
                print("Could not read image from camera")
        # FIX ME - stop and cleanup thread
        # Something bad happened

    def read(self):
        with self.read_lock:
            frame = self.frame.copy()
            grabbed = self.grabbed
        return grabbed, frame

    def release(self):
        if self.video_capture != None:
            self.video_capture.release()
            self.video_capture = None
        # Now kill the thread
        if self.read_thread != None:
            self.read_thread.join()


""" 
gstreamer_pipeline returns a GStreamer pipeline for capturing from the CSI camera
Flip the image by setting the flip_method (most common values: 0 and 2)
display_width and display_height determine the size of each camera pane in the window on the screen
Default 1920x1080
"""


def gstreamer_pipeline(
    sensor_id=0,
    

# 0 - 3264 x 2464 @ 21fps gain 1-10
# 1 - 3264 x 1848 @ 28 fps gain 1-10
# 2 - 1920 x 1080 @ 30 fps gain 1-10
# 3 - 1280 x 720 @ 60 fps gain 1-10
# 4 - 1280 x 720 @ 120 fps gain 1-10
    sensor_mode=3,
    capture_width=1920,
    capture_height=1080,
    display_width=1920,
    display_height=1080,
    framerate=60,
    flip_method=0,
    noise_reduction=0,
    framerateout=30
):
    return (
        "nvarguscamerasrc sensor-id=%d sensor-mode=%d gainrange=\"1.0 3.0\" ispdigitalgainrange='1 1' exposurecompensation=1 aeantibanding=1 ! " # gainrange=\"1.0 3.0\" ispdigitalgainrange='1 1' exposurecompensation=1 aeantibanding=1
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx, framerate=(fraction)%d/1 ! "
        "videobalance saturation=1.2 ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            sensor_id,
            sensor_mode,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
            framerateout
        )
    )

FPS = 30
OUT_FPS = 30 # jetson is not good at writing to disk apparently, so it needs time

WIDTH_PX = 640 # 960 # 640 # 1920
HEIGHT_PX = 480 #360 # 540 # 480 # 1080
VIDEO_FILE_MAX_DURATION_SEC = 10

def run_cameras():
    window_title = "Dual CSI Cameras"
    left_camera = CSI_Camera()
    left_camera.open(
        gstreamer_pipeline(
            sensor_id=0,
            capture_width=960, #1920,
            capture_height=540, #1080,
            flip_method=0,
            framerate=FPS,
            display_width=WIDTH_PX, #960,
            display_height=HEIGHT_PX, #540,
        )
    )
    left_camera.start()

    right_camera = CSI_Camera()
    right_camera.open(
        gstreamer_pipeline(
            sensor_id=1,
            capture_width=960, #1920,
            capture_height=540, #1080,
            flip_method=0,
            framerate=FPS,
            display_width=WIDTH_PX, #960,
            display_height=HEIGHT_PX, #540,
        )
    )
    right_camera.start()

    if left_camera.video_capture.isOpened(): # and right_camera.video_capture.isOpened():    
        cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)

        try:
            # video writing loop
            while True:
                # write to file
                timestamp = int(datetime.datetime.now().timestamp())
                output_file = f'/home/gratheon/Desktop/gratheon/python-client/cam/{timestamp}.mp4'

                writer = cv2.VideoWriter(
                    f'appsrc ! video/x-raw, format=BGR ! videoconvert ! nvvidconv ! video/x-raw(memory:NVMM), format=I420 ! nvvidconv ! video/x-raw, format=I420 ! omxh264enc ! video/x-h264, stream-format=byte-stream ! h264parse ! mp4mux ! filesink location={output_file}',
                    cv2.CAP_GSTREAMER, 0, OUT_FPS,(WIDTH_PX,HEIGHT_PX))
                    
                if not writer.isOpened():
                    print("Failed to open output")
                    exit()

                start_time = time.time()
                lastFrameWrite = time.time()

                # camera reading loop

                TIME_TO_FRAME = 0.06
                lastCycleTime = time.time()
                while True:
                    _, left_image = left_camera.read()
                    _, right_image = right_camera.read()

                    # Use numpy to place images next to each other
                    camera_images = np.hstack((left_image, right_image)) 

                    # Check to see if the user closed the window
                    # Under GTK+ (Jetson Default), WND_PROP_VISIBLE does not work correctly. Under Qt it does
                    # GTK - Substitute WND_PROP_AUTOSIZE to detect if window has been closed by user
                    if cv2.getWindowProperty(window_title, cv2.WND_PROP_AUTOSIZE) >= 0:
                        # cv2.imshow(window_title, left_image)
                        cv2.imshow(window_title, camera_images)
                    else:
                        break
                    
                    if not is_day_time():
                        print("night time, skipping video storage & upload")
                        cv2.waitKey(5)
                        writer.release()
                        continue

                    if left_image is None:
                        break

                    TIME_TO_FRAME = time.time() - lastCycleTime
                    isFrameDelayElapsed = time.time() - lastFrameWrite >= (1/OUT_FPS)-TIME_TO_FRAME
                    lastCycleTime = time.time()

                    if(isFrameDelayElapsed):
                        print(f'fps:{1/(time.time() - lastFrameWrite)} time: {time.time() - lastFrameWrite}')
                        writer.write(left_image)
                        # writer.write(right_image)
                        lastFrameWrite = time.time()


                    isVideoLengthReached = time.time() - start_time >= VIDEO_FILE_MAX_DURATION_SEC

                    # exit on escape or q
                    if cv2.waitKey(5) & 0xFF == 27 or cv2.waitKey(1) & 0xFF == ord('q') or isVideoLengthReached:
                        writer.release()
                        break

                if is_day_time():
                    upload_file_async(output_file)
        finally:

            left_camera.stop()
            left_camera.release()
            right_camera.stop()
            right_camera.release()
        cv2.destroyAllWindows()
    else:
        print("Error: Unable to open both cameras")
        left_camera.stop()
        left_camera.release()
        right_camera.stop()
        right_camera.release()

def is_day_time():
    current_time = datetime.datetime.now().time()
    return current_time >= datetime.time(8, 0) and current_time < datetime.time(18, 0)


if __name__ == "__main__":
    delete_old_mp4_files()
    run_cameras()
