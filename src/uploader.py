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


def upload_file_async(file_path, start_time_utc):
    # Define a function to upload the file asynchronously
    upload_thread = threading.Thread(target=uploadAndRemove, args=(file_path, start_time_utc))
    upload_thread.start()

def uploadAndRemove(output_file: str, start_time_utc: datetime):
    # Retrieve environment variables
    bearer_token = os.getenv("API_TOKEN")
    box_id = os.getenv("SECTION_ID")

    if not bearer_token or not box_id:
        print("Error: Please set the API_TOKEN and BOX_ID environment variables.")
        print("Skipping video upload for testing purposes.")
        return

    try:
        # Make multipart/form-data request
        with open(output_file, 'rb') as file:
            response = requests.post(
                'https://video.gratheon.com/graphql', 
                headers={
                    'Authorization': f'Bearer {bearer_token}'
                }, 
                data={
                    "operations": json.dumps({
                        'query': (
                            'mutation UploadVideo($file: Upload!, $boxId: ID!, $startTime: DateTime!) {'
                            '  uploadGateVideo(file: $file, boxId: $boxId, startTime: $startTime)'
                            '}'
                        ),
                        'variables': {
                            'file': None,
                            'boxId': box_id,
                            'startTime': start_time_utc.isoformat()
                        }
                    }),
                    "map": json.dumps({ "0": ["variables.file"] })
                },
                files = {
                    "0": file, # Adjust content type if needed
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


def delete_old_mp4_files():
    directory = "./videos"
    max_age_hours = 1
    now = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    for file_path in glob.glob(os.path.join(directory, '*.mp4')):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - file_mtime > max_age:
            os.remove(file_path)
            print(f"Deleted {file_path}")
