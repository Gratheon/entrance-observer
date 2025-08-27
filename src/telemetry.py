import threading
import requests

def report_telemetry_async(beesIn, beesOut, bearer_token, hiveId, boxId, base_url):
    telemetry_thread = threading.Thread(target=report_telemetry, args=(beesIn, beesOut, bearer_token, hiveId, boxId, base_url))
    telemetry_thread.start()

def report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url):
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
    print("Payload to be sent:", payload)

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
            print("Counts reported successfully")
        else:
            print("Error reporting counts:", response.status_code)

        return response.text
    except Exception as e:
        print(f"Error sending telemetry: {e}")
        raise e