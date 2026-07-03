import threading
import requests
import json
from datetime import datetime
import os
import app_settings
import uploader

def _resolve_telemetry_upload_url(base_url, telemetry_settings=None):
    telemetry_settings = telemetry_settings or app_settings.get_telemetry_settings()
    full_url = telemetry_settings.get("upload_url") or os.getenv("TELEMETRY_UPLOAD_URL")
    if full_url:
        return full_url

    path = telemetry_settings.get("upload_path") or os.getenv("TELEMETRY_UPLOAD_PATH", "/entrance/v1/movement")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url.rstrip('/')}{path}"

def _ensure_telemetry_dir():
    """Ensures the telemetry directory exists."""
    telemetry_dir = app_settings.get_storage_settings().get("telemetry_dir") or os.getenv("TELEMETRY_DIR", "./telemetry")
    print(f"ℹ️ Ensuring telemetry directory exists at: {telemetry_dir}")
    try:
        os.makedirs(telemetry_dir, exist_ok=True)
        return telemetry_dir
    except OSError as e:
        fallback_dir = os.path.abspath("./telemetry")
        print(f"⚠️ Failed to prepare telemetry dir ({e}). Falling back to: {fallback_dir}")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

def save_track_history_locally(track_history, frame_shape):
    """Saves track history data to a local jsonl file with daily rotation."""
    try:
        telemetry_dir = _ensure_telemetry_dir()
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        file_path = os.path.join(telemetry_dir, f"track_history_{date_str}.jsonl")
        print(f"📝 Attempting to write track history to: {file_path}")
        
        timestamp = datetime.utcnow().isoformat()
        
        # Convert coordinates to integers and defaultdict to a regular dict
        serializable_history = {
            int(k): [[int(round(coord[0])), int(round(coord[1]))] for coord in v]
            for k, v in track_history.items()
        }

        data = {
            "timestamp": timestamp,
            "frame_dimensions": {
                "height": frame_shape[0],
                "width": frame_shape[1]
            },
            "track_history": serializable_history,
        }
        with open(file_path, "a") as f:
            f.write(json.dumps(data) + "\n")
        print(f"✅ Track history saved locally to {file_path}.")
    except Exception as e:
        print(f"❌ Error saving track history locally: {e}")

def save_telemetry_locally(metrics_data):
    """Saves telemetry data to a local jsonl file with daily rotation."""
    try:
        telemetry_dir = _ensure_telemetry_dir()
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        file_path = os.path.join(telemetry_dir, f"metrics_{date_str}.jsonl")
        print(f"📝 Attempting to write telemetry to: {file_path}")

        timestamp = datetime.utcnow().isoformat()
        data = {
            "timestamp": timestamp,
            "metrics": metrics_data,
        }
        with open(file_path, "a") as f:
            f.write(json.dumps(data) + "\n")
        print(f"✅ Telemetry saved locally to {file_path}.")
    except Exception as e:
        print(f"❌ Error saving telemetry locally: {e}")


def report_heatmap_trajectories_async(track_history, frame_shape):
    upload_thread = threading.Thread(target=report_heatmap_trajectories, args=(track_history, frame_shape))
    upload_thread.daemon = True
    upload_thread.start()


def report_heatmap_trajectories(track_history, frame_shape):
    """Sends raw bee trajectories to gate-video-stream for centralized daily heatmap generation."""
    telemetry_settings = app_settings.get_telemetry_settings()
    box_id = telemetry_settings.get("section_id")
    if not telemetry_settings.get("api_token") or not box_id:
        print("ℹ️ Skipping heatmap trajectory upload because API token or section ID is missing.")
        return

    if not track_history:
        print("ℹ️ Skipping heatmap trajectory upload because track history is empty.")
        return

    serializable_history = {
        str(k): [[int(round(coord[0])), int(round(coord[1]))] for coord in v]
        for k, v in track_history.items()
        if v
    }
    if not serializable_history:
        return

    payload = {
        "boxId": box_id,
        "timestamp": datetime.utcnow().isoformat(),
        "frameDimensions": {
            "height": frame_shape[0],
            "width": frame_shape[1],
        },
        "trackHistory": serializable_history,
    }

    try:
        response = uploader._post_video_service_json('/api/entrance-heatmaps/trajectories', payload, timeout=120)
        if response.status_code in (200, 201):
            print("✅ Heatmap trajectories uploaded successfully.")
        else:
            print("❌ Error uploading heatmap trajectories:", response.status_code)
            print(response.text)
    except Exception as error:
        print(f"❌ Error sending heatmap trajectories: {error}")

def report_telemetry_async(metrics_data, bearer_token=None, hiveId=None, boxId=None, base_url=None, telemetry_settings=None):
    telemetry_thread = threading.Thread(target=report_telemetry, args=(metrics_data, bearer_token, hiveId, boxId, base_url, telemetry_settings))
    telemetry_thread.start()

def report_telemetry(metrics_data, bearer_token=None, hiveId=None, boxId=None, base_url=None, telemetry_settings=None):
    telemetry_settings = telemetry_settings or app_settings.get_telemetry_settings()
    bearer_token = bearer_token or telemetry_settings.get("api_token")
    hiveId = hiveId or telemetry_settings.get("hive_id")
    boxId = boxId or telemetry_settings.get("section_id")
    base_url = base_url or telemetry_settings.get("base_url") or "https://telemetry.gratheon.com"

    save_telemetry_locally(metrics_data)
    if not bearer_token or not boxId:
        print("Error: Please provide API token and section ID in app settings.")
        print("Skipping telemetry upload for testing purposes.")
        return

    # Prepare the payload
    payload = {
        "boxId": boxId,
        "hiveId": hiveId,
        "beesIn": metrics_data.get("bees_in", 0),
        "beesOut": metrics_data.get("bees_out", 0),
        "netFlow": metrics_data.get("net_flow", 0),
        "avgSpeed": metrics_data.get("avg_speed_px_per_frame", 0),
        "p95Speed": metrics_data.get("p95_speed_px_per_frame", 0),
        "stationaryBees": metrics_data.get("stationary_bees_count", 0),
        "detectedBees": metrics_data.get("detected_bees", 0),
        "beeInteractions": metrics_data.get("bee_interactions", 0),
    }

    # Print the payload
    print("📡 Payload to be sent:", payload)
    endpoint_url = _resolve_telemetry_upload_url(base_url, telemetry_settings)
    print("📡 Telemetry endpoint:", endpoint_url)

    try:
        # Make multipart/form-data request
        response = requests.post(
            endpoint_url,
            headers={
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            },
            json=payload,  # Use json parameter instead of data
            timeout=120,
            allow_redirects=True
        )

        if response.status_code == 200:
            print("✅ Counts reported successfully")
        else:
            print("❌ Error reporting counts:", response.status_code)
            print(response.text)

        return response.text
    except Exception as e:
        print(f"❌ Error sending telemetry: {e}")
        raise e
