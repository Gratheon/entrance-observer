import datetime
import importlib
import json
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import cv2  # noqa: F401
except ModuleNotFoundError:
    fake_cv2 = types.ModuleType('cv2')
    fake_cv2.CAP_GSTREAMER = 0
    sys.modules['cv2'] = fake_cv2

original_ultralytics = sys.modules.get('ultralytics')
fake_ultralytics = types.ModuleType('ultralytics')
fake_ultralytics.YOLO = lambda *args, **kwargs: object()
sys.modules['ultralytics'] = fake_ultralytics
main = importlib.import_module('src.main')
if original_ultralytics is None:
    sys.modules.pop('ultralytics', None)
else:
    sys.modules['ultralytics'] = original_ultralytics
sys.modules.pop('counter', None)


def write_metrics(path, timestamp, metrics):
    with open(path, 'a') as metrics_file:
        metrics_file.write(json.dumps({
            'timestamp': timestamp,
            'metrics': metrics,
        }) + '\n')


def test_load_recent_bee_counts_history_restores_last_24h(tmp_path, monkeypatch):
    now_utc = datetime.datetime(2026, 7, 1, 15, 0, tzinfo=datetime.timezone.utc)
    metrics_file = tmp_path / 'metrics_2026-07-01.jsonl'
    write_metrics(metrics_file, '2026-06-30T14:59:00', {'bees_in': 1, 'bees_out': 0})
    write_metrics(metrics_file, '2026-06-30T15:01:00', {'bees_in': 2, 'bees_out': 1})
    write_metrics(metrics_file, '2026-07-01T15:00:00+00:00', {'bees_in': 3, 'bees_out': 1})
    metrics_file.write_text(metrics_file.read_text() + 'not-json\n')

    monkeypatch.setattr(main, 'get_storage_settings', lambda: {'telemetry_dir': str(tmp_path)})

    with main.bee_counts_history_lock:
        main.bee_counts_history.clear()
    main.load_recent_bee_counts_history(now_utc)

    with main.bee_counts_history_lock:
        rows = list(main.bee_counts_history)

    assert [row['bees_in'] for row in rows] == [2, 3]
    assert all('time' in row for row in rows)


def test_append_bee_count_prunes_entries_older_than_24h():
    now_local = datetime.datetime(2026, 7, 1, 15, 0, 0)
    old_time = (now_local - datetime.timedelta(hours=24, seconds=1)).strftime(main.BEE_COUNTS_TIME_FORMAT)

    with main.bee_counts_history_lock:
        main.bee_counts_history.clear()
        main.bee_counts_history.append({'time': old_time, 'bees_in': 1})

    main.append_bee_count({'bees_in': 5, 'bees_out': 2}, now_local=now_local)

    with main.bee_counts_history_lock:
        rows = list(main.bee_counts_history)
        main.bee_counts_history.clear()

    assert rows == [{
        'bees_in': 5,
        'bees_out': 2,
        'time': now_local.strftime(main.BEE_COUNTS_TIME_FORMAT),
    }]


def test_bee_counts_api_returns_pruned_history():
    now_local = datetime.datetime.now()
    old_time = (now_local - datetime.timedelta(hours=25)).strftime(main.BEE_COUNTS_TIME_FORMAT)
    recent_time = (now_local - datetime.timedelta(hours=1)).strftime(main.BEE_COUNTS_TIME_FORMAT)

    with main.bee_counts_history_lock:
        main.bee_counts_history.clear()
        main.bee_counts_history.append({'time': old_time, 'bees_in': 1})
        main.bee_counts_history.append({'time': recent_time, 'bees_in': 2})

    client = main.app.test_client()
    response = client.get('/api/bee_counts')

    with main.bee_counts_history_lock:
        main.bee_counts_history.clear()

    assert response.status_code == 200
    assert response.get_json() == [{'time': recent_time, 'bees_in': 2}]
