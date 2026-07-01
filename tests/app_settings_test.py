import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import app_settings


def test_storage_settings_group_related_storage_values_from_env(monkeypatch):
    monkeypatch.setenv('VIDEOS_DIR', './custom-videos')
    monkeypatch.setenv('VIDEO_RETENTION_MINUTES', '60')
    monkeypatch.setenv('DETECT_VIDEO_RETENTION_MINUTES', '5')
    monkeypatch.setenv('TELEMETRY_DIR', './custom-telemetry')
    monkeypatch.setenv('TELEMETRY_RETENTION_DAYS', '14')
    monkeypatch.setenv('RUNS_DIR', './custom-runs')
    monkeypatch.setenv('RUNS_RETENTION_DAYS', '3')
    monkeypatch.setenv('MIN_FREE_DISK_MB', '512')
    monkeypatch.setenv('MAX_MANAGED_STORAGE_MB', '2048')
    monkeypatch.setenv('DELETE_UPLOADED_VIDEOS', 'true')

    storage = app_settings.get_storage_settings({'storage': {}})

    assert storage['videos_dir'] == './custom-videos'
    assert storage['video_retention_minutes'] == 60
    assert storage['detect_video_retention_minutes'] == 5
    assert storage['telemetry_dir'] == './custom-telemetry'
    assert storage['telemetry_retention_days'] == 14
    assert storage['runs_dir'] == './custom-runs'
    assert storage['runs_retention_days'] == 3
    assert storage['min_free_disk_mb'] == 512
    assert storage['max_managed_storage_mb'] == 2048
    assert storage['delete_uploaded_videos'] is True


def test_storage_settings_keep_explicit_file_values_over_env(monkeypatch):
    monkeypatch.setenv('TELEMETRY_DIR', './env-telemetry')
    monkeypatch.setenv('RUNS_RETENTION_DAYS', '3')

    storage = app_settings.get_storage_settings({
        'storage': {
            'telemetry_dir': './file-telemetry',
            'runs_retention_days': 9,
        },
    })

    assert storage['telemetry_dir'] == './file-telemetry'
    assert storage['runs_retention_days'] == 9


def test_video_settings_support_confidence_threshold_from_env(monkeypatch):
    monkeypatch.setenv('CONFIDENCE', '0.75')

    video = app_settings.get_video_settings({'video': {}})

    assert video['bee_confidence_threshold'] == 0.75


def test_video_settings_keep_explicit_confidence_threshold_over_env(monkeypatch):
    monkeypatch.setenv('CONFIDENCE', '0.75')

    video = app_settings.get_video_settings({
        'video': {
            'bee_confidence_threshold': 0.6,
        },
    })

    assert video['bee_confidence_threshold'] == 0.6


def test_video_settings_support_max_detections_from_env(monkeypatch):
    monkeypatch.setenv('BEE_MAX_DETECTIONS', '1500')

    video = app_settings.get_video_settings({'video': {}})

    assert video['bee_max_detections'] == 1500


def test_load_raw_settings_uses_tracked_template_when_local_settings_are_missing(monkeypatch, tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    template_path = data_dir / 'settings.example.json'
    template_path.write_text('{"telemetry": {"hive_id": "template-hive"}}\n', encoding='utf-8')

    monkeypatch.setattr(app_settings, 'SETTINGS_PATH', str(data_dir / 'settings.json'))
    monkeypatch.setattr(app_settings, 'SETTINGS_TEMPLATE_PATH', str(template_path))

    settings = app_settings.load_raw_settings()

    assert settings['telemetry']['hive_id'] == 'template-hive'
