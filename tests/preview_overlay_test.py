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


def test_camera_status_api_returns_current_status():
    main.set_camera_status('missing', 'Camera not found', 'Connect USB camera')

    response = main.app.test_client().get('/api/camera_status')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['state'] == 'missing'
    assert payload['message'] == 'Camera not found'
    assert payload['detail'] == 'Connect USB camera'
    assert payload['updated_at'].endswith('Z')


def test_camera_status_frame_is_rendered_when_no_preview_frame():
    main.set_camera_status('missing', 'Camera not found', 'Connect USB camera')

    frame = main.create_camera_status_frame(width=320, height=180)

    assert frame.shape == (180, 320, 3)
    assert np.count_nonzero(frame) > 0


def test_generate_frames_yields_placeholder_when_frame_is_missing(monkeypatch):
    main.set_camera_status('missing', 'Camera not found', 'Connect USB camera')
    monkeypatch.setattr(main.time, 'sleep', lambda *_args, **_kwargs: None)

    chunk = next(main.generate_frames(lambda: None))

    assert chunk.startswith(b'--frame\r\nContent-Type: image/jpeg')
    assert b'\xff\xd8' in chunk
