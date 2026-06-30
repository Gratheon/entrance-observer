import importlib
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

fake_ultralytics = types.ModuleType('ultralytics')
fake_ultralytics.YOLO = lambda *args, **kwargs: object()
sys.modules.setdefault('ultralytics', fake_ultralytics)

main = importlib.import_module('src.main')


@pytest.fixture
def videos_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'get_storage_settings', lambda: {'videos_dir': str(tmp_path)})
    return tmp_path


def write_file(path, contents=b'content'):
    path.write_bytes(contents)
    return path


def test_delete_single_video(videos_dir):
    video = write_file(videos_dir / 'recording.mp4')
    other_video = write_file(videos_dir / 'other.mov')

    assert main.delete_recorded_video(video.name) is True

    assert not video.exists()
    assert other_video.exists()


def test_delete_single_video_rejects_invalid_paths_and_types(videos_dir):
    text_file = write_file(videos_dir / 'notes.txt')
    outside_video = write_file(videos_dir.parent / 'outside.mp4')

    with pytest.raises(ValueError):
        main.delete_recorded_video('../outside.mp4')

    with pytest.raises(ValueError):
        main.delete_recorded_video(text_file.name)

    assert text_file.exists()
    assert outside_video.exists()


def test_delete_all_recorded_videos_keeps_non_video_files(videos_dir):
    first_video = write_file(videos_dir / 'first.mp4')
    second_video = write_file(videos_dir / 'second.webm')
    text_file = write_file(videos_dir / 'notes.txt')

    deleted_count, errors = main.delete_all_recorded_videos()

    assert deleted_count == 2
    assert errors == []
    assert not first_video.exists()
    assert not second_video.exists()
    assert text_file.exists()


def test_delete_video_api(videos_dir):
    video = write_file(videos_dir / 'api-video.mp4')
    client = main.app.test_client()

    response = client.delete(f'/api/videos/{video.name}')

    assert response.status_code == 200
    assert response.get_json()['deleted'] == video.name
    assert not video.exists()


def test_delete_all_videos_api(videos_dir):
    write_file(videos_dir / 'one.mp4')
    write_file(videos_dir / 'two.mkv')
    text_file = write_file(videos_dir / 'notes.txt')
    client = main.app.test_client()

    response = client.delete('/api/videos')

    assert response.status_code == 200
    assert response.get_json()['deleted_count'] == 2
    assert list(videos_dir.glob('*.mp4')) == []
    assert list(videos_dir.glob('*.mkv')) == []
    assert text_file.exists()
