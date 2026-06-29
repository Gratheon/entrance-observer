import copy
import json
import os
from typing import Any, Dict, Optional

SETTINGS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")
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
    "dir": "./telemetry",
    "video_upload_url": "https://video.gratheon.com/graphql",
}

DEFAULT_NIGHT_MODE_SETTINGS = {
    "enabled": True,
    "day_start_hour": 6,
    "day_end_hour": 22,
}

DEFAULT_SETTINGS = {
    "camera_properties": DEFAULT_CAMERA_PROPERTIES,
    "detection_line_coefficient": 0.5,
    "entrance_position": "bottom",
    "telemetry": DEFAULT_TELEMETRY_SETTINGS,
    "night_mode": DEFAULT_NIGHT_MODE_SETTINGS,
}

TELEMETRY_ENV_MAP = {
    "api_token": "API_TOKEN",
    "hive_id": "HIVE_ID",
    "section_id": "SECTION_ID",
    "base_url": "TELEMETRY_BASE_URL",
    "upload_path": "TELEMETRY_UPLOAD_PATH",
    "upload_url": "TELEMETRY_UPLOAD_URL",
    "dir": "TELEMETRY_DIR",
    "video_upload_url": "VIDEO_UPLOAD_URL",
}

NIGHT_MODE_ENV_MAP = {
    "day_start_hour": "DAY_START_HOUR",
    "day_end_hour": "DAY_END_HOUR",
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


def load_raw_settings() -> Dict[str, Any]:
    try:
        with open(SETTINGS_PATH, "r") as settings_file:
            return json.load(settings_file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        print(f"⚠️ Failed to parse settings file {SETTINGS_PATH}: {error}")
        return {}


def merge_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    return _deep_merge(DEFAULT_SETTINGS, settings or {})


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


def has_effective_api_token(raw_settings: Optional[Dict[str, Any]] = None) -> bool:
    return bool(get_telemetry_settings(raw_settings).get("api_token"))
