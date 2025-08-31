# Use NVIDIA's official L4T base image for Jetson devices
# This image includes the necessary drivers and libraries for GPU access
# FROM dustynv/l4t-pytorch:r36.2.0
FROM ultralytics/ultralytics:latest-jetson-jetpack6

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
# - python3 and pip for running the application
# - git for cloning repositories if needed
# - v4l-utils to help with camera device management
# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     # git \
#     # v4l-utils \
#     && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_RETRIES=10
ENV PIP_TRUSTED_HOST=pypi.org
ENV PIP_INDEX_URL=https://pypi.org/simple
#ENV PIP_ONLY_BINARY=:all:
ENV PYTHONPATH=.

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libx11-xcb1 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*


# Copy the application files into the container
COPY . .

# Install the Python dependencies from requirements.jetson.txt
#RUN python3 -m pip install --no-cache-dir -v --index-url=https://pypi.org/simple --trusted-host pypi.org -r requirements.jetson.txt

RUN python3 -m pip install --no-cache-dir -v requests-toolbelt
RUN python3 -m pip install --no-cache-dir -v ultralytics==8.3
RUN python3 -m pip install --no-cache-dir -v "shapely>=2.0"
RUN python3 -m pip install --no-cache-dir -v "lapx>=0.5"
RUN python3 -m pip install --no-cache-dir -v python-dotenv==1.0
RUN python3 -m pip install --no-cache-dir -v Flask==3.1
RUN python3 -m pip install --no-cache-dir -v opencv-python-headless

# Install the specific PyTorch wheel for Jetson with CUDA support
# This is crucial for GPU acceleration of the YOLO model
# RUN wget https://pypi.jetson-ai-lab.io/jp6/cu126/+f/de1/5388b8f70e4e1/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=de15388b8f70e4e17a05b23a4ae1f55a288c91449371bb8aeeb69184d40be17f && \
#     pip3 install torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl && \
#     rm torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl

# Set the default command to run the application
CMD ["python3", "src/main.py"]
