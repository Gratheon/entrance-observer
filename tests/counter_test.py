import os
import sys
import cv2
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import counter

def test_count_bees():
    #ARRANGE
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'videos', '314.mp4'))
    cap = cv2.VideoCapture(video_path)
    
    frames_for_counting = []
    frame_shape = None
    fps = cap.get(cv2.CAP_PROP_FPS)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_shape is None:
            frame_shape = frame.shape[:2]

        results = counter.model.track(frame, persist=True)
        capture_time = time.monotonic()
        frames_for_counting.append((frame, results, capture_time))

    cap.release()
    
    # ACT
    beesIn, beesOut, detectedBees, _ = counter.countBees(frames_for_counting, frame_shape=frame_shape, writer_fps=fps)

    # ASSERT
    assert beesIn == 27, "Expected bees in the video"
    assert beesOut == 15, "Expected bees out of the video"
    assert detectedBees > 0, "Expected detected bees"
