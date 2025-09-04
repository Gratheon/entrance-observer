import threading
import requests
import json
from datetime import datetime

def save_track_history_locally(track_history, frame_shape):
    """Saves track history data to a local jsonl file."""
    try:
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
        with open("track_history.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")
        print("✅ Track history saved locally.")
    except Exception as e:
        print(f"❌ Error saving track history locally: {e}")

def save_telemetry_locally(metrics_data):
    """Saves telemetry data to a local jsonl file."""
    try:
        timestamp = datetime.utcnow().isoformat()
        data = {
            "timestamp": timestamp,
            "metrics": metrics_data,
        }
        with open("metrics.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")
        print("✅ Telemetry saved locally.")
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
