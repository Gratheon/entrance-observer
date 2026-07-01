import copy
import json
import os
from typing import Any, Dict, Optional

SETTINGS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")
)
SETTINGS_TEMPLATE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "settings.example.json")
)

DEFAULT_CAMERA_PROPERTIES = {
    "brightness": 40,
    "contrast": 4,
    "saturation": 70,
    "gain": 0,
    "exposure": -6,
    "white_balance_temperature": 4000,
    "gamma": 78,
    "sharpness": 128,
    "backlight": 1,
}

DEFAULT_TELEMETRY_SETTINGS = {
    "api_token": "",
    "hive_id": "",
    "section_id": "",
    "base_url": "https://telemetry.gratheon.com",
    "upload_path": "/entrance/v1/movement",
    "upload_url": "",
    "video_upload_url": "https://video.gratheon.com/graphql",
}

DEFAULT_NIGHT_MODE_SETTINGS = {
    "enabled": True,
    "day_start_hour": 6,
    "day_end_hour": 22,
}

DEFAULT_VIDEO_SETTINGS = {
    "fps": 30,
    "width_px": 640,
    "height_px": 480,
    "detect_video_width": 320,
    "detect_video_height": 240,
    "video_chunk_length_sec": 20,
    "auto_calibrate_fps": True,
    "upload_videos_enabled": True,
    "upload_max_fps": 0,
    "bee_confidence_threshold": 0.5,
    "bee_max_detections": 1000,
}

DEFAULT_STORAGE_SETTINGS = {
    "videos_dir": "./videos",
    "telemetry_dir": "./telemetry",
    "runs_dir": "./runs",
    "video_retention_minutes": 1440,
    "detect_video_retention_minutes": 10,
    "telemetry_retention_days": 30,
    "runs_retention_days": 7,
    "min_free_disk_mb": 1024,
    "max_managed_storage_mb": 0,
    "delete_uploaded_videos": False,
}

DEFAULT_DETECTION_RECTANGLE = {
    "x": 0.25,
    "y": 0.35,
    "width": 0.5,
    "height": 0.2,
}

DEFAULT_SETTINGS = {
    "camera_properties": DEFAULT_CAMERA_PROPERTIES,
    "detection_line_coefficient": 0.5,
    "counting_mode": "line",
    "detection_rectangle": DEFAULT_DETECTION_RECTANGLE,
    "entrance_position": "bottom",
    "telemetry": DEFAULT_TELEMETRY_SETTINGS,
    "night_mode": DEFAULT_NIGHT_MODE_SETTINGS,
    "video": DEFAULT_VIDEO_SETTINGS,
    "storage": DEFAULT_STORAGE_SETTINGS,
}

TELEMETRY_ENV_MAP = {
    "api_token": "API_TOKEN",
    "hive_id": "HIVE_ID",
    "section_id": "SECTION_ID",
    "base_url": "TELEMETRY_BASE_URL",
    "upload_path": "TELEMETRY_UPLOAD_PATH",
    "upload_url": "TELEMETRY_UPLOAD_URL",
    "video_upload_url": "VIDEO_UPLOAD_URL",
}

NIGHT_MODE_ENV_MAP = {
    "day_start_hour": "DAY_START_HOUR",
    "day_end_hour": "DAY_END_HOUR",
}

VIDEO_ENV_MAP = {
    "fps": "FPS",
    "width_px": "WIDTH_PX",
    "height_px": "HEIGHT_PX",
    "detect_video_width": "DETECT_VIDEO_WIDTH",
    "detect_video_height": "DETECT_VIDEO_HEIGHT",
    "video_chunk_length_sec": "VIDEO_CHUNK_LENGTH_SEC",
    "upload_max_fps": "UPLOAD_MAX_FPS",
    "bee_max_detections": "BEE_MAX_DETECTIONS",
}

STORAGE_ENV_MAP = {
    "videos_dir": "VIDEOS_DIR",
    "telemetry_dir": "TELEMETRY_DIR",
    "runs_dir": "RUNS_DIR",
    "video_retention_minutes": "VIDEO_RETENTION_MINUTES",
    "detect_video_retention_minutes": "DETECT_VIDEO_RETENTION_MINUTES",
    "telemetry_retention_days": "TELEMETRY_RETENTION_DAYS",
    "runs_retention_days": "RUNS_RETENTION_DAYS",
    "min_free_disk_mb": "MIN_FREE_DISK_MB",
    "max_managed_storage_mb": "MAX_MANAGED_STORAGE_MB",
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _env_bool(name: str) -> Optional[bool]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str) -> Optional[int]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        print(f"⚠️ Ignoring invalid integer env var {name}={raw_value!r}")
        return None


def _env_float(name: str) -> Optional[float]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except ValueError:
        print(f"⚠️ Ignoring invalid float env var {name}={raw_value!r}")
        return None


def load_raw_settings() -> Dict[str, Any]:
    for candidate_path in (SETTINGS_PATH, SETTINGS_TEMPLATE_PATH):
        try:
            with open(candidate_path, "r") as settings_file:
                return json.load(settings_file)
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as error:
            print(f"⚠️ Failed to parse settings file {candidate_path}: {error}")
            return {}
    return {}


def merge_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    merged = _deep_merge(DEFAULT_SETTINGS, settings or {})
    legacy_telemetry_dir = (settings or {}).get("telemetry", {}).get("dir")
    if legacy_telemetry_dir and not (settings or {}).get("storage", {}).get("telemetry_dir"):
        merged["storage"]["telemetry_dir"] = legacy_telemetry_dir
    return merged


def save_settings_file(settings: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as settings_file:
        json.dump(settings, settings_file, indent=4)
        settings_file.write("\n")


def get_telemetry_settings(raw_settings: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    raw_settings = load_raw_settings() if raw_settings is None else raw_settings
    merged = merge_settings(raw_settings)
    telemetry = copy.deepcopy(merged["telemetry"])
    raw_telemetry = raw_settings.get("telemetry", {}) if isinstance(raw_settings, dict) else {}

    for key, env_name in TELEMETRY_ENV_MAP.items():
        env_value = os.getenv(env_name)
        if env_value and (key not in raw_telemetry or telemetry.get(key) in (None, "")):
            telemetry[key] = env_value

    return telemetry


def get_night_mode_settings(raw_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw_settings = load_raw_settings() if raw_settings is None else raw_settings
    merged = merge_settings(raw_settings)
    night_mode = copy.deepcopy(merged["night_mode"])
    raw_night_mode = raw_settings.get("night_mode", {}) if isinstance(raw_settings, dict) else {}

    if "enabled" not in raw_night_mode:
        enabled_from_env = _env_bool("NIGHT_MODE_ENABLED")
        if enabled_from_env is not None:
            night_mode["enabled"] = enabled_from_env

    for key, env_name in NIGHT_MODE_ENV_MAP.items():
        if key not in raw_night_mode:
            env_value = _env_int(env_name)
            if env_value is not None:
                night_mode[key] = env_value

    return night_mode


def _settings_with_env_ints(section_name: str, env_map: Dict[str, str], raw_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    raw_settings = load_raw_settings() if raw_settings is None else raw_settings
    merged = merge_settings(raw_settings)
    section = copy.deepcopy(merged[section_name])
    raw_section = raw_settings.get(section_name, {}) if isinstance(raw_settings, dict) else {}

    for key, env_name in env_map.items():
        if key in raw_section:
            continue
        if isinstance(section.get(key), int):
            env_value = _env_int(env_name)
            if env_value is not None:
                section[key] = env_value
        else:
            env_value = os.getenv(env_name)
            if env_value:
                section[key] = env_value

    return section


def get_video_settings(raw_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    video = _settings_with_env_ints("video", VIDEO_ENV_MAP, raw_settings)
    raw_settings = load_raw_settings() if raw_settings is None else raw_settings
    raw_video = raw_settings.get("video", {}) if isinstance(raw_settings, dict) else {}

    if "bee_confidence_threshold" not in raw_video:
        confidence_from_env = _env_float("CONFIDENCE")
        if confidence_from_env is not None:
            video["bee_confidence_threshold"] = min(max(confidence_from_env, 0.0), 1.0)

    if "auto_calibrate_fps" not in raw_video:
        enabled_from_env = _env_bool("AUTO_CALIBRATE_FPS")
        if enabled_from_env is not None:
            video["auto_calibrate_fps"] = enabled_from_env
    if "upload_videos_enabled" not in raw_video:
        enabled_from_env = _env_bool("UPLOAD_VIDEOS_ENABLED")
        if enabled_from_env is not None:
            video["upload_videos_enabled"] = enabled_from_env

    return video


def get_storage_settings(raw_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    storage = _settings_with_env_ints("storage", STORAGE_ENV_MAP, raw_settings)
    raw_settings = load_raw_settings() if raw_settings is None else raw_settings
    raw_storage = raw_settings.get("storage", {}) if isinstance(raw_settings, dict) else {}

    if "delete_uploaded_videos" not in raw_storage:
        enabled_from_env = _env_bool("DELETE_UPLOADED_VIDEOS")
        if enabled_from_env is not None:
            storage["delete_uploaded_videos"] = enabled_from_env

    return storage


def has_effective_api_token(raw_settings: Optional[Dict[str, Any]] = None) -> bool:
    return bool(get_telemetry_settings(raw_settings).get("api_token"))
