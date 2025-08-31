# gratheon / entrance-observer

Beehive entrance video processing client script.
Intended to be deployed on edge on NVidia Jetson Orin / Jetson Nano / Mac or similar GPU-capable machines.

https://github.com/user-attachments/assets/a3243245-34a8-4626-a990-f7e34b7b8ff6


## Features

- Video input stream. Best to use 4K USB camera. Streams data into memory and then store it on disk with as 10 sec chunks
	- Tries to autodetect camera if its not found
- Uploads video chunks to gratheon web-app for playback (assuming wifi/lan is present)
	- Uses H.264 codec for video compression (~2mb for 10 sec)
- Runs bee detection using YOLO ML model


Note. I Tried dual CSI cameras too, it could work too, but quality of optics was not sufficient (too much fish-eye)

## Running
```
PYTHONPATH=. python3 src/main.py
```

### Running with Docker (Recommended for Jetson)

This method uses Docker to run the application in a containerized environment, which is the recommended approach for Jetson devices. It simplifies dependency management and ensures a consistent runtime environment.

1.  **Allow X11 Forwarding on Host**: Before running the container, you'll need to allow connections to your X server from the container. You can do this by running the following command on your host machine:
    ```bash
    xhost +
    ```
2.  **Start the Container**: With the `Dockerfile` and `docker-compose.yml` files in the `entrance-observer` directory, you can start the application with:
    ```bash
    docker-compose up --build
    ```
This will build the Docker image and start the container. The application's UI should appear on your screen.

## Installation

```
git clone https://github.com/Gratheon/entrance-observer.git
cp .env.example .env

pip install -r requirements.txt
```
- Generate API token in https://app.gratheon.com/account
- Open your hive entrance view, ex https://app.gratheon.com/apiaries/55/hives/68/box/250 and use BOX_ID from the end of URL, ex. 250.
- Edit `.env` and configure values

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


## Supported environments
✅ Mac OSX
✅ Jetson Orin Nano
	- Ubuntu 22
	- Python 3.10
	- Jetpack 6
	- cuDNN 8 

### Jetson Orin setup
After running pip install of main dependencies, you must ensure to install pytorch with cuda support
```
dpkg-query --show nvidia-jetpack # assuming you are on 6.0

# wget https://developer.download.nvidia.com/compute/redist/jp/v60dp/pytorch/torch-2.2.0a0+81ea7a4.nv24.01-cp310-cp310-linux_aarch64.whl

wget https://pypi.jetson-ai-lab.io/jp6/cu126/+f/de1/5388b8f70e4e1/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=de15388b8f70e4e17a05b23a4ae1f55a288c91449371bb8aeeb69184d40be17f
```



## Listing cameras
To list which cameras correspond to which devices in linux, you can use:
```
sudo apt install v4l-utils
v4l2-ctl --list-devices
 ```


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

- We upload a 10 sec video chunks to gratheon web-app for playback feature
- We separate webcam from inference mostly because inference is dockerized while webcam uses local window for preview.

```mermaid
flowchart LR
	subgraph Edge
	entrance-observer --"read with native python to file"--> webcam["📷 webcam"]
	entrance-observer -."write video file locally" .-> filesystem["🖴 filesystem"]
	entrance-observer -."run inference from file" .-> counter --"read"--> filesystem
	counter -."run inference".-> yolov8["👁️‍🗨 YOLOv8"] --"write _detect videos"--> filesystem
    uploader --"read file"--> filesystem
    
	end

	subgraph Cloud
        entrance-observer -."upload".-> uploader --"upload video chunk"--> gate-video-stream
	    entrance-observer --"send edge-inference results"--> telemetry-api[<a href="https://github.com/Gratheon/telemetry-api">telemetry-api</a>]
	end
```
