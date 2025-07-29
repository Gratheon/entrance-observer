# gratheon / entrance-observer

Beehive entrance video processing service. Manages video inferencing. 
Intended to be deployed on edge on NVidia Jetson Orin or NVidia Jetson Nano



https://github.com/user-attachments/assets/a3243245-34a8-4626-a990-f7e34b7b8ff6



## Features

- Uses 4K USB video camera stream as input, stores it into 10 sec chunks
  - Tried dual CSI cameras too, it could work too, but quality was not sufficient
- Uploads video chunks to gratheon web-app for playback
- Runs bee detection

## Installation & Usage

```
git clone https://github.com/Gratheon/entrance-observer.git
```
- Generate API token in https://app.gratheon.com/account
- Open your hive entrance view, ex https://app.gratheon.com/apiaries/55/hives/68/box/250 and use BOX_ID from the end of URL, ex. 250.
- Rename `.env.example` to `.env` and fill in the required fields

### Configuration
We use env vars and we load them from `.env` file for ease of management.
Some of them:
```
API_TOKEN=...
HIVE_ID=...

# section is a box (vertical part of the hive), get the number from the URL
SECTION_ID=...
```

### Platform Support

The entrance-observer now supports multiple platforms:

- **Linux** (NVidia Jetson, Raspberry Pi, etc.) - Uses V4L2 backend with `/dev/video*` devices
- **macOS** - Uses AVFoundation backend with camera indices (0, 1, 2, etc.)
- **Windows** - Uses DirectShow backend

### Camera Configuration

#### Automatic Detection
By default, the system will automatically detect and use available cameras:

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

#### Manual Camera Selection
You can specify a camera device manually by modifying the `startObserverClient()` call in `main.py`:

**Linux:**
```python
startObserverClient("/dev/video0")  # Use specific video device
```

**macOS:**
```python
startObserverClient("0")  # Use camera index 0 (built-in camera)
startObserverClient("1")  # Use camera index 1 (external camera)
```

#### Testing Camera Setup
Use the included test script to verify camera functionality:

```bash
python3 test_camera.py           # Test all available cameras
python3 test_camera.py 0         # Test specific camera (macOS/Windows)
python3 test_camera.py /dev/video0  # Test specific device (Linux)
```

## Architecture

- We upload a 10 sec video chunks to gratheon web-app for playback feature
- We separate webcam from inference mostly because inference is dockerized while webcam uses local window for preview.

```mermaid
flowchart LR
	subgraph Edge
	entrance-observer --"read with native python to file"--> webcam["📷 webcam"]
	entrance-observer -."write video file locally" .-> filesystem["🖴 filesystem"]
	entrance-observer -."run inference from file" .-> counter --"read"--> filesystem
	counter -."run inference".-> yolov8["👁️‍🗨 YOLOv8"]
    uploader --"read file"--> filesystem
    
	end

	subgraph Cloud
        entrance-observer -."upload".-> uploader --"upload video chunk"--> gate-video-stream
	    entrance-observer --"send edge-inference results"--> telemetry-api[<a href="https://github.com/Gratheon/telemetry-api">telemetry-api</a>]
	end
```