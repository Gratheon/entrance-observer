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


class FakeIdList:
    def __init__(self, ids):
        self.ids = ids

    def int(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.ids


class FakeBoxList(list):
    def cpu(self):
        return self


class FakeBoxes:
    def __init__(self, boxes, ids):
        self.is_track = True
        self.xyxy = FakeBoxList(boxes)
        self.id = FakeIdList(ids)


class FakeResult:
    def __init__(self, boxes, ids):
        self.boxes = FakeBoxes(boxes, ids)


def fake_frame_with_track(center_x, center_y, track_id=1, frame_size=(100, 100)):
    half_size = 2
    box = [center_x - half_size, center_y - half_size, center_x + half_size, center_y + half_size]
    frame = cv2.UMat(frame_size[1], frame_size[0], cv2.CV_8UC3).get()
    return frame, [FakeResult([box], [track_id])], time.monotonic()


def test_count_bees_line_mode_remains_backward_compatible():
    frames_for_counting = [
        fake_frame_with_track(50, 40),
        fake_frame_with_track(50, 60),
    ]

    beesIn, beesOut, detectedBees, _ = counter.countBees(
        frames_for_counting,
        detection_line_coefficient=0.5,
        frame_shape=(100, 100),
        writer_fps=30,
        entrance_position='bottom',
        counting_mode='line',
    )

    assert beesIn == 1
    assert beesOut == 0
    assert detectedBees == 1


def test_count_bees_rectangle_mode_counts_entering_and_exiting_area():
    rectangle = {"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2}
    frames_for_counting = [
        fake_frame_with_track(20, 50),
        fake_frame_with_track(50, 50),
        fake_frame_with_track(80, 50),
    ]

    beesIn, beesOut, detectedBees, _ = counter.countBees(
        frames_for_counting,
        frame_shape=(100, 100),
        writer_fps=30,
        counting_mode='rectangle',
        detection_rectangle=rectangle,
    )

    assert beesIn == 1
    assert beesOut == 1
    assert detectedBees == 1
