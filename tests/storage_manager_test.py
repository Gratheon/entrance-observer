import os
import sys
import time
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import storage_manager


def test_delete_files_older_than_deduplicates_glob_matches(tmp_path):
    video = tmp_path / '1782902654.mp4'
    video.write_bytes(b'video')
    old_timestamp = time.time() - 3600
    os.utime(video, (old_timestamp, old_timestamp))

    storage_manager.delete_files_older_than(
        str(tmp_path),
        ['*.mp4', '*.mp4'],
        timedelta(seconds=1),
        'video',
    )

    assert not video.exists()


def test_delete_files_older_than_ignores_files_removed_before_stat(tmp_path, monkeypatch):
    missing_file = str(tmp_path / '1782902624.mp4')
    monkeypatch.setattr(storage_manager, '_iter_files', lambda _directory, _patterns: [missing_file])

    storage_manager.delete_files_older_than(
        str(tmp_path),
        ['*.mp4'],
        timedelta(seconds=1),
        'video',
    )
