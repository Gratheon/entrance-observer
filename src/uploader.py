import json
import os
import requests
import threading
from datetime import datetime
from dotenv import load_dotenv

import app_settings
import storage_manager

# Load environment variables from .env file
load_dotenv()


def upload_file_async(file_path, detections_file_path, start_time_utc):
    upload_thread = threading.Thread(target=uploadAndRemove, args=(file_path, detections_file_path, start_time_utc))
    upload_thread.start()


def uploadAndRemove(output_file: str, detections_file: str, start_time_utc: datetime):
    video_settings = app_settings.get_video_settings()
    if not video_settings.get("upload_videos_enabled", True):
        print("☁️ Video upload disabled in app settings.")
        storage_manager.cleanup_storage()
        return

    settings = app_settings.get_telemetry_settings()
    bearer_token = settings.get("api_token")
    box_id = settings.get("section_id")
    upload_url = settings.get("video_upload_url") or "https://video.gratheon.com/graphql"

    if not bearer_token or not box_id:
        print("Error: Please set API token and section ID in app settings.")
        print("Skipping video upload for testing purposes.")
        storage_manager.cleanup_storage()
        return

    uploaded_successfully = False
    try:
        with open(output_file, 'rb') as file, open(detections_file, 'rb') as detectionsFile:
            response = requests.post(
                upload_url,
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
            try:
                response_json = response.json()
            except ValueError:
                response_json = None

            if response_json and response_json.get("errors"):
                print("❌ Video upload GraphQL errors:", response_json["errors"])
            elif response_json and response_json.get("data", {}).get("uploadGateVideo") is True:
                print("✅ Video uploaded successfully")
                uploaded_successfully = True
            elif response_json and response_json.get("data", {}).get("uploadGateVideo") is False:
                print("❌ Video upload rejected by gate-video-stream (uploadGateVideo=false)")
            else:
                print("⚠️ Video upload response did not contain expected uploadGateVideo result")
        else:
            print("❌ Error uploading video:", response.status_code)

        print(response.text)

    except Exception as e:
        print(f"Error during video upload: {e}")

    if uploaded_successfully and app_settings.get_storage_settings().get("delete_uploaded_videos", False):
        for path in {output_file, detections_file}:
            try:
                os.remove(path)
                print(f"🧹 Deleted uploaded video: {path}")
            except OSError as error:
                print(f"⚠️ Could not delete uploaded video {path}: {error}")

    storage_manager.cleanup_storage()


def delete_old_mp4_files():
    storage_manager.cleanup_storage()
