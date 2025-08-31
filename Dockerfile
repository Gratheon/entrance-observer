# Use NVIDIA's official L4T base image for Jetson devices
# This image includes the necessary drivers and libraries for GPU access
FROM nvcr.io/nvidia/l4t-base:r35.1.0

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
# - python3 and pip for running the application
# - git for cloning repositories if needed
# - v4l-utils to help with camera device management
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the application files into the container
COPY . .

# Install the Python dependencies from requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install the specific PyTorch wheel for Jetson with CUDA support
# This is crucial for GPU acceleration of the YOLO model
RUN wget https://pypi.jetson-ai-lab.io/jp6/cu126/+f/de1/5388b8f70e4e1/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=de15388b8f70e4e17a05b23a4ae1f55a288c91449371bb8aeeb69184d40be17f && \
    pip3 install torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl && \
    rm torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl

# Set the default command to run the application
CMD ["python3", "src/main.py"]
