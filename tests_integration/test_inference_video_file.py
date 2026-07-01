import os
import sys
import cv2
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import counter

def test_inference_from_video_file_with_UI():
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))
    
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

    # The test name mentions UI, so let's test the video writing capability.
    output_video_path = "test_inference_output.mp4"
    
    beesIn, beesOut, detectedBees, _ = counter.countBees(
        frames_for_counting, 
        output_video_path=output_video_path, 
        writer_fps=fps, 
        frame_shape=frame_shape
    )

    print(f"Bees In: {beesIn}, Bees Out: {beesOut}")
    assert beesIn == 28
    assert beesOut == 13

    # Clean up the generated video file
    if os.path.exists(output_video_path):
        os.remove(output_video_path)
