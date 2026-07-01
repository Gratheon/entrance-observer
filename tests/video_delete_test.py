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


def test_delete_single_video_removes_playback_cache(videos_dir):
    video = write_file(videos_dir / 'recording.mp4')
    cache_dir = videos_dir / '.playback_cache'
    cache_dir.mkdir()
    stale_cache = write_file(cache_dir / 'recording.mp4.123.7.h264.mp4', b'cache')
    other_cache = write_file(cache_dir / 'other.mp4.123.7.h264.mp4', b'cache')

    assert main.delete_recorded_video(video.name) is True

    assert not stale_cache.exists()
    assert other_cache.exists()


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


def test_local_video_supports_range_requests_for_remote_browser_playback(videos_dir, monkeypatch):
    video = write_file(videos_dir / 'range-video.mp4', b'0123456789')
    monkeypatch.setattr(main, 'has_browser_supported_video_codec', lambda path: True)
    client = main.app.test_client()

    response = client.get(f'/local_videos/{video.name}', headers={'Range': 'bytes=2-5'})

    assert response.status_code == 206
    assert response.data == b'2345'
    assert response.headers['Content-Range'] == 'bytes 2-5/10'
    assert response.headers['Accept-Ranges'] == 'bytes'


def test_local_video_rejects_invalid_paths_and_types(videos_dir):
    write_file(videos_dir / 'safe.mp4')
    client = main.app.test_client()

    assert client.get('/local_videos/../safe.mp4').status_code == 404
    assert client.get('/local_videos/notes.txt').status_code == 404


def test_browser_playback_video_path_transcodes_unsupported_codec(videos_dir, monkeypatch):
    source = write_file(videos_dir / 'opencv-fallback.mp4')
    monkeypatch.setattr(main, 'has_browser_supported_video_codec', lambda path: False)
    monkeypatch.setattr(main.shutil, 'which', lambda command: f'/usr/bin/{command}' if command == 'ffmpeg' else None)

    def fake_run(command, **kwargs):
        assert command[0] == '/usr/bin/ffmpeg'
        assert '-c:v' in command
        assert 'libx264' in command
        tmp_output_path = command[-1]
        write_file(type(source)(tmp_output_path), b'h264-content')
        return types.SimpleNamespace(returncode=0, stdout='', stderr='')

    monkeypatch.setattr(main.subprocess, 'run', fake_run)

    playback_path = main.get_browser_playback_video_path(str(source))

    assert playback_path != str(source)
    assert playback_path.endswith('.h264.mp4')
    assert os.path.exists(playback_path)
    assert type(source)(playback_path).read_bytes() == b'h264-content'


def test_browser_playback_video_path_reuses_cached_transcode(videos_dir, monkeypatch):
    source = write_file(videos_dir / 'cached.mp4')
    monkeypatch.setattr(main, 'has_browser_supported_video_codec', lambda path: False)
    cache_path = main.get_playback_cache_path(str(source))
    write_file(type(source)(cache_path), b'cached-content')
    monkeypatch.setattr(main.shutil, 'which', lambda command: f'/usr/bin/{command}')

    def fail_run(*args, **kwargs):
        raise AssertionError('ffmpeg should not run when cached playback file exists')

    monkeypatch.setattr(main.subprocess, 'run', fail_run)

    assert main.get_browser_playback_video_path(str(source)) == cache_path
