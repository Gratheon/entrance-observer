import json
import os
import time
import cv2
import requests
import threading
from requests_toolbelt.multipart.encoder import MultipartEncoder
import glob
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def upload_file_async(file_path, detections_file_path, start_time_utc):
    # Define a function to upload the file asynchronously
    upload_thread = threading.Thread(target=uploadAndRemove, args=(file_path, detections_file_path, start_time_utc))
    upload_thread.start()

def uploadAndRemove(output_file: str, detections_file: str, start_time_utc: datetime):
    # Retrieve environment variables
    bearer_token = os.getenv("API_TOKEN")
    box_id = os.getenv("SECTION_ID")

    if not bearer_token or not box_id:
        print("Error: Please set the API_TOKEN and BOX_ID environment variables.")
        print("Skipping video upload for testing purposes.")
        return

    try:
        # Make multipart/form-data request
        with open(output_file, 'rb') as file, open(detections_file, 'rb') as detectionsFile:
            response = requests.post(
                'https://video.gratheon.com/graphql',
                headers={
                    'Authorization': f'Bearer {bearer_token}'
                },
                data={
                    "operations": json.dumps({
                        'query': (
                            'mutation UploadVideo($file: Upload!, $detectionsFile: Upload!, $boxId: ID!, $startTime: DateTime!) {'
                            '  uploadGateVideo(file: $file, detectionsFile: $detectionsFile, boxId: $boxId, startTime: $startTime)'
                            '}'
                        ),
                        'variables': {
                            'file': None,
                            'detectionsFile': None,
                            'boxId': box_id,
                            'startTime': start_time_utc.isoformat()
                        }
                    }),
                    "map": json.dumps({
                        "0": ["variables.file"],
                        "1": ["variables.detectionsFile"]
                    })
                },
                files={
                    "0": file,
                    "1": detectionsFile,
                },
                timeout=120,
                allow_redirects=True
            )

        if response.status_code == 200:
            print("Video uploaded successfully")
        else:
            print("Error uploading video:", response.status_code)

        print(response.text)

    except Exception as e:
        print(f"Error during video upload: {e}")

    # remove file after uploading, you can leave it if you want a local cache
    # but you need enough storage to not run out of space
    # os.remove(output_file)
    # os.remove(detections_file)


def delete_old_mp4_files():
    directory = "./videos"
    retention_minutes = os.getenv("VIDEO_RETENTION_MINUTES", "1440")  # Default to 24 hours
    max_age_minutes = int(retention_minutes)
    now = datetime.now()
    max_age = timedelta(minutes=max_age_minutes)

    for file_path in glob.glob(os.path.join(directory, '*.mp4')):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - file_mtime > max_age:
            os.remove(file_path)
            print(f"Deleted {file_path}")
