import threading
import requests
import json
from datetime import datetime
import os

def _ensure_telemetry_dir():
    """Ensures the telemetry directory exists."""
    telemetry_dir = "/app/telemetry"
    print(f"ℹ️ Ensuring telemetry directory exists at: {telemetry_dir}")
    if not os.path.exists(telemetry_dir):
        print(f"⚠️ Telemetry directory not found. Creating it...")
        os.makedirs(telemetry_dir)
    return telemetry_dir

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

def report_telemetry_async(metrics_data, bearer_token, hiveId, boxId, base_url):
    telemetry_thread = threading.Thread(target=report_telemetry, args=(metrics_data, bearer_token, hiveId, boxId, base_url))
    telemetry_thread.start()

def report_telemetry(metrics_data, bearer_token, hiveId, boxId, base_url):
    save_telemetry_locally(metrics_data)
    if not bearer_token or not boxId:
        print("Error: Please provide API_TOKEN and SECTION_ID.")
        print("Skipping telemetry upload for testing purposes.")
        return

    # Prepare the payload
    payload = {
        "boxId": boxId,
        "hiveId": hiveId,
        "beesIn": metrics_data["bees_in"],
        "beesOut": metrics_data["bees_out"],
        "netFlow": metrics_data["net_flow"],
        "avgSpeed": metrics_data["avg_speed_px_per_frame"],
        "p95Speed": metrics_data["p95_speed_px_per_frame"],
        "stationaryBees": metrics_data["stationary_bees_count"],
    }

    # Print the payload
    print("📡 Payload to be sent:", payload)

    try:
        # Make multipart/form-data request
        response = requests.post(
            f'{base_url}/entrance/v1/movement',
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
