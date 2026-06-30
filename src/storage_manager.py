import glob
import os
import shutil
from datetime import datetime, timedelta
from typing import Iterable, List, Tuple

import app_settings


def ensure_managed_directories() -> None:
    storage = app_settings.get_storage_settings()
    for key in ("videos_dir", "telemetry_dir", "runs_dir"):
        directory = storage.get(key)
        if directory:
            os.makedirs(directory, exist_ok=True)


def _remove_file(path: str, reason: str) -> bool:
    try:
        os.remove(path)
        print(f"🧹 Deleted {path}: {reason}")
        return True
    except FileNotFoundError:
        return False
    except OSError as error:
        print(f"⚠️ Failed to delete {path}: {error}")
        return False


def _iter_files(directory: str, patterns: Iterable[str]) -> Iterable[str]:
    if not directory or not os.path.isdir(directory):
        return []

    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
    return [path for path in files if os.path.isfile(path)]


def delete_files_older_than(directory: str, patterns: Iterable[str], max_age: timedelta, label: str) -> None:
    now = datetime.now()
    for file_path in _iter_files(directory, patterns):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - file_mtime > max_age:
            _remove_file(file_path, f"{label} retention exceeded")


def _managed_files(storage: dict) -> List[Tuple[float, int, str]]:
    managed = []
    patterns_by_dir = {
        storage.get("videos_dir", "./videos"): ["*.mp4"],
        storage.get("telemetry_dir", "./telemetry"): ["*.jsonl"],
        storage.get("runs_dir", "./runs"): ["**/*"],
    }
    for directory, patterns in patterns_by_dir.items():
        for file_path in _iter_files(directory, patterns):
            try:
                stat = os.stat(file_path)
            except OSError:
                continue
            managed.append((stat.st_mtime, stat.st_size, file_path))
    managed.sort(key=lambda item: item[0])
    return managed


def _bytes_to_mb(value: int) -> float:
    return value / 1024 / 1024


def enforce_disk_limits() -> None:
    storage = app_settings.get_storage_settings()
    videos_dir = storage.get("videos_dir", "./videos")
    disk_root = os.path.abspath(videos_dir if os.path.isdir(videos_dir) else ".")
    min_free_bytes = int(storage.get("min_free_disk_mb", 1024)) * 1024 * 1024
    max_managed_bytes = int(storage.get("max_managed_storage_mb", 0)) * 1024 * 1024

    try:
        usage = shutil.disk_usage(disk_root)
    except OSError as error:
        print(f"⚠️ Could not read disk usage for {disk_root}: {error}")
        return

    managed_files = _managed_files(storage)
    managed_bytes = sum(size for _, size, _ in managed_files)

    def over_limits() -> bool:
        free_too_low = usage.free < min_free_bytes
        managed_too_large = max_managed_bytes > 0 and managed_bytes > max_managed_bytes
        return free_too_low or managed_too_large

    while managed_files and over_limits():
        _, size, file_path = managed_files.pop(0)
        if _remove_file(
            file_path,
            f"disk guard free={_bytes_to_mb(usage.free):.0f}MB managed={_bytes_to_mb(managed_bytes):.0f}MB",
        ):
            managed_bytes -= size
            try:
                usage = shutil.disk_usage(disk_root)
            except OSError:
                break


def cleanup_storage() -> None:
    storage = app_settings.get_storage_settings()
    ensure_managed_directories()

    videos_dir = storage.get("videos_dir", "./videos")
    delete_files_older_than(
        videos_dir,
        ["*[!_]??????.mp4", "*.mp4"],
        timedelta(minutes=int(storage.get("video_retention_minutes", 1440))),
        "video",
    )
    delete_files_older_than(
        videos_dir,
        ["*_detect.mp4"],
        timedelta(minutes=int(storage.get("detect_video_retention_minutes", 10))),
        "detection video",
    )
    delete_files_older_than(
        storage.get("telemetry_dir", "./telemetry"),
        ["*.jsonl"],
        timedelta(days=int(storage.get("telemetry_retention_days", 30))),
        "telemetry",
    )
    delete_files_older_than(
        storage.get("runs_dir", "./runs"),
        ["**/*"],
        timedelta(days=int(storage.get("runs_retention_days", 7))),
        "runs",
    )
    enforce_disk_limits()
