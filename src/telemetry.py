import threading
import requests
import json
from datetime import datetime

def save_telemetry_locally(beesIn, beesOut, bees):
    """Saves telemetry data to a local jsonl file."""
    try:
        timestamp = datetime.utcnow().isoformat()
        data = {
            "timestamp": timestamp,
            "bees_in": beesIn,
            "bees_out": beesOut,
            "bees": bees,
        }
        with open("metrics.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")
        print("✅ Telemetry saved locally.")
    except Exception as e:
        print(f"❌ Error saving telemetry locally: {e}")

def report_telemetry_async(beesIn, beesOut, bees, bearer_token, hiveId, boxId, base_url):
    telemetry_thread = threading.Thread(target=report_telemetry, args=(beesIn, beesOut, bees, bearer_token, hiveId, boxId, base_url))
    telemetry_thread.start()

def report_telemetry(beesIn, beesOut, bees, bearer_token, hiveId, boxId, base_url):
    save_telemetry_locally(beesIn, beesOut, bees)
    if not bearer_token or not boxId:
        print("Error: Please provide API_TOKEN and SECTION_ID.")
        print("Skipping telemetry upload for testing purposes.")
        return

    # Prepare the payload
    payload = {
        "boxId": boxId,
        "hiveId": hiveId,
        "beesIn": beesIn,
        "beesOut": beesOut,
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
