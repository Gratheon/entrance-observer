import importlib
import os
import sys
import types

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

fake_ultralytics = types.ModuleType('ultralytics')
fake_ultralytics.YOLO = lambda *args, **kwargs: object()
sys.modules.setdefault('ultralytics', fake_ultralytics)

main = importlib.import_module('src.main')


def test_draw_tracking_trail_renders_polyline_without_labels():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    track = [(10, 10), (20, 20), (30, 20)]

    main.draw_tracking_trail(frame, track, track_id=42)

    assert np.count_nonzero(frame) > 0
    assert frame[20, 20].any(), 'Expected trail polyline to pass through the bee path'


def test_draw_tracking_trail_skips_single_point_tracks():
    frame = np.zeros((80, 80, 3), dtype=np.uint8)

    main.draw_tracking_trail(frame, [(10, 10)], track_id=42)

    assert np.count_nonzero(frame) == 0


def test_detection_runtime_settings_are_read_from_current_settings(monkeypatch):
    current_settings = {
        'bee_confidence_threshold': 0.2,
        'bee_max_detections': 1000,
    }
    monkeypatch.setattr(main, 'get_video_settings', lambda: current_settings.copy())

    first = main.get_detection_runtime_settings()
    current_settings['bee_confidence_threshold'] = 0.8
    current_settings['bee_max_detections'] = 2500
    second = main.get_detection_runtime_settings()

    assert first == {'bee_confidence_threshold': 0.2, 'bee_max_detections': 1000}
    assert second == {'bee_confidence_threshold': 0.8, 'bee_max_detections': 2500}
