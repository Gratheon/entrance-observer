# gratheon / entrance-observer

Beehive entrance video processing client app.
Intended to be deployed on edge on NVidia Jetson Orin / Jetson Nano / Mac or similar GPU-capable machines.

https://github.com/user-attachments/assets/a3243245-34a8-4626-a990-f7e34b7b8ff6


## Features

- **Video capture**. Best to use 4K USB camera. Streams data into memory and then store it on disk with as 30 sec chunks (configureable)
	- Tries to autodetect camera if its not found
- **Detects bees** using YOLO 11 model with custom bee detection weights.
- **Tracks bees movements and speeds** and estimates their movement speeds. Stores tracks for potential behavioural analysis
- **Counts incoming and outgoing bees**. Calculates net flow. Useful to estimate forager loss.

- **Video upload**. Uploads video chunks to [gratheon web-app](https://github.com/Gratheon/web-app/) for playback (assuming wifi/lan is present)
	- Uses H.264 codec for video compression if available (usually on mac)
		- Falls back to mp4 ifcodec is not available (jetson orin nano)
	- Skips video upload if no bees were incoming/outgoing to avoid unnecessary traffic

- **Web UI** for local network access and configuration (with streaming) with a simple log of:
	- detected bees
	- incoming/outgoing bees
	- max log is the past 10h
	- sleep at night time (22:00-06:00)
- **Telemetry** - metrics  are sent to [gratheon web-app](https://github.com/Gratheon/web-app/) for aggregate statistics


## Metrics

The application collects a rich set of metrics to provide a comprehensive overview of the beehive's activity. These metrics are saved locally to `metrics.jsonl` and, if configured, sent to the Gratheon telemetry service.

### Core Metrics

-   **`bees_in`**: The number of bees that crossed the virtual line to enter the hive.
-   **`bees_out`**: The number of bees that crossed the virtual line to exit the hive.
-   **`detected_bees`**: The total number of unique bees detected in the frame during the processing period.

### Derived Metrics

-   **`net_flow`**: Calculated as `bees_in - bees_out`, this metric indicates the net change in the hive's population. A positive value suggests more bees are returning than leaving, while a negative value could be an early indicator of swarming or other issues.
-   **`avg_speed_px_per_frame`**: The average speed of all tracked bees, measured in pixels per frame. This provides an insight into the general flight speed of the bees.
-   **`p95_speed_px_per_frame`**: The 95th percentile of bee speed. This helps to understand the top speed of the fastest bees, filtering out potential outliers.
-   **`stationary_bees_count`**: The number of bees that are considered stationary (i.e., their total movement is below a certain threshold). This can be useful for identifying guard bees or bees performing orientation flights.

### Raw Track History

For in-depth analysis and potential model retraining, the application also saves the raw track history of each bee to a separate `track_history.jsonl` file. Each entry in this file contains:

-   **`timestamp`**: The UTC timestamp of the recording.
-   **`frame_dimensions`**: The height and width of the video frame, which is crucial for interpreting the coordinate data.
-   **`track_history`**: A dictionary where each key is a unique bee ID and the value is a list of `[x, y]` integer coordinates representing the bee's path.

### Notes
- I Tried dual CSI cameras too, it could work too, but quality of optics was not sufficient (too much fish-eye)
- Note we are not _streaming_ video to gratheon.com as we do not adjust bandwidth/video quality depending on connectivity. So reliable network connection is essential. We are uploading chunks.

## Installation

- After manual installation of the entrance observer device, make sure to correctly position camera, so that hive entrance is **down**.
- Setup your edge devices to prepare the service

```
git clone https://github.com/Gratheon/entrance-observer.git
cp .env.example .env

pip install -r requirements.txt
```
- Generate API token in https://app.gratheon.com/account
- Open your hive entrance view, ex https://app.gratheon.com/apiaries/55/hives/68/box/250 and use BOX_ID from the end of URL, ex. 250.
- Edit `.env` and configure values (see Configuration section below)
- Run service (see Running section below)
- Open service web ui (see URL section below)

### Tuning
- Once service runs, make sure its detection speed is below 10 sec video segment. Otherwise you risk of having detection being slower than recording, thus crashing the service. Ex. in logs:
```
Time taken for countBeesAndReportTelemetry: 7.31 seconds
```
- Reduce width/height or FPS if detection is too slow
- Check wether videos are uploaded to the web-app and are accessible for playback there.


### Configuration
We use env vars and we load them from `.env` file for ease of management.

|var|description|example|
|--|--|--|
|HIVE_ID|identifier of the hive. Can be found in the gratheon.com hive URL|364|
|SECTION_ID|hive section (box). Can be found in the URL|1944|
|API_TOKEN|authentication token| 9f23616a52-2a51-4369-96d3-237a456eedb5
|CAMERA_DEVICE|numerical number for the device. For Linux, you can set it to `/dev/video0`.|0
|FPS|frame rate of the camera|30|
|WIDTH_PX|width of the output video. |960|
|HEIGHT_PX|height of the video. will be ignored if it does not match aspect ratio of the camera, will get calculated based on WIDTH_PX |720|
|CONFIDENCE|detection confidence threshold, from 0 to 1|0.5|
|DETECTION_LINE|coefficient for the vertical position of the counting line, from 0 to 1|0.5|
|VIDEO_CHUNK_LENGTH_SEC|length of the video chunks in seconds. Smaller values result in more files created. Higher values in larger video file size getting uploaded and higher probability of upload as some bee may get detected coming in/out. Higher values also give more room to increase resolution/fps for best performance fit | 60 |
|DAY_START_HOUR|The hour (0-23) when the service should start processing video. Set to DAY_END_HOUR to disable the sleep schedule.|6|
|DAY_END_HOUR|The hour (0-23) when the service should stop processing video and sleep. Set to DAY_START_HOUR to disable the sleep schedule.|22|


#### Listing cameras
To list which cameras correspond to which devices in linux, you can use:
```
sudo apt install v4l-utils
v4l2-ctl --list-devices
 ```



## Supported environments
Tested on these environments:
✅ Mac OSX
✅ Jetson Orin Nano
	- Ubuntu 22
	- Python 3.10
	- Jetpack 6
	- cuDNN 8 


## Running natively (Mac)
```
PYTHONPATH=. python3 src/main.py
```

### Running with Docker (Jetson Orin)

```bash
docker compose up --build
```



## URLs
|URL| Description |
|--|--|
|http://localhost:3030 | Entrance observer service web UI with local web cam stream, available after startup |



## Development

### Unit tests

We use [`just`](https://github.com/casey/just) to run commands instead of `make`. Under the hood it relies on pytest. Unit tests check simple functions:

```
just test
```

### Integration tests
Integration tests rely on more complexity and side effects. It needs/checks
- cameras to be present
- GPU inference to works
- network request reaches gratheon telemetry endpoint
```
just test-integration
```


### Platform Support

The entrance-observer now supports multiple platforms:

- **Linux** (NVidia Jetson, Raspberry Pi, etc.) - Uses V4L2 backend with `/dev/video*` devices
- **macOS** - Uses AVFoundation backend with camera indices (0, 1, 2, etc.)
- **Windows** - Uses DirectShow backend


## Architecture

The video processing pipeline is designed to be robust and efficient, handling both the capture of raw video frames and their subsequent encoding into a compressed format suitable for storage and analysis.

### Video Processing Workflow

The application uses OpenCV for both video capture and encoding. The `cv2.VideoCapture` function is used to interface with the camera hardware, and the `cv2.VideoWriter` function is used to encode the video. This approach was chosen for its simplicity and reliability across different platforms.
