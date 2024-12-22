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


def upload_file_async(file_path):
    # Define a function to upload the file asynchronously
    upload_thread = threading.Thread(target=uploadAndRemove, args=(file_path,))
    upload_thread.start()

def uploadAndRemove(output_file: str):
    # Retrieve environment variables
    bearer_token = os.getenv("API_TOKEN")
    box_id = os.getenv("BOX_ID")

    if not bearer_token or not box_id:
        print("Error: Please set the API_TOKEN and BOX_ID environment variables.")
        return

    # Make multipart/form-data request
    response = requests.post(
        'https://video.gratheon.com/graphql', 
        headers={
            'Authorization': f'Bearer {bearer_token}'
        }, 
        data={
            "operations": json.dumps({
                'query': (
                    'mutation UploadVideo($file: Upload!, $boxId: ID!) {'
                    '  uploadGateVideo(file: $file, boxId: $boxId)'
                    '}'
                ),
                'variables': {
                    'file': None,
                    'boxId': box_id
                }
            }),
            "map": json.dumps({ "0": ["variables.file"] })
        },
        files = {
            "0": open(output_file, 'rb'), # Adjust content type if needed
        },
        timeout=120, 
        allow_redirects=True
    )

    if response.status_code == 200:
        print("Video uploaded successfully")
    else:
        print("Error uploading video:", response.status_code)
        
    print(response.text)

    # remove file after uploading, you can leave it if you want a local cache
    # but you need enough storage to not run out of space
    # os.remove(output_file)


def delete_old_mp4_files():
    directory = "./cam"
    max_age_hours = 1
    now = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    for file_path in glob.glob(os.path.join(directory, '*.mp4')):
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - file_mtime > max_age:
            os.remove(file_path)
            print(f"Deleted {file_path}")