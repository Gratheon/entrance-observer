#!/bin/bash

# ==============================================================================
# Camera Bandwidth Optimization Script for Jetson Orin Nano
# ==============================================================================
# This script addresses USB bandwidth limitations that can prevent cameras from
# reaching their full potential FPS. It applies several system-level tweaks to
# prioritize performance and stability for USB video devices.

echo "🚀 Optimizing camera bandwidth and USB performance..."

# --- Check for Root Privileges ---
# Many of the commands in this script require root (administrator) privileges
# to modify system files and settings. This check ensures the script is run
# with 'sudo'.
if [ "$EUID" -ne 0 ]; then
    echo "⚠️ This script needs to be run as root for USB optimizations"
    echo "Usage: sudo ./optimize_camera_bandwidth.sh"
    exit 1
fi

# ==============================================================================
# USB Core Optimizations
# ==============================================================================

# --- Increase USBFS Memory Buffer ---
# The USB File System (usbfs) is used to transfer data from USB devices.
# Increasing its memory buffer from the default (often 16MB) to 32MB provides
# more space for high-bandwidth data streams (like video), reducing the risk
# of dropped frames or data loss.
echo "📷 Optimizing USB settings for camera bandwidth..."
echo 32 > /sys/module/usbcore/parameters/usbfs_memory_mb

# --- Disable USB Autosuspend for Cameras ---
# Autosuspend is a power-saving feature that puts USB devices to sleep when idle.
# For a camera that is constantly streaming, this can cause delays and stutters
# as the device wakes up. This loop finds all connected video devices and
# disables autosuspend for them, ensuring they are always ready.
echo "🔌 Disabling USB autosuspend for video devices..."
for device in /sys/bus/usb/devices/*/product; do
    if [ -f "$device" ]; then
        product=$(cat "$device" 2>/dev/null)
        if [[ "$product" == *"Camera"* ]] || [[ "$product" == *"camera"* ]] || [[ "$product" == *"Video"* ]]; then
            device_path=$(dirname "$device")
            echo "Found camera device: $product"
            # A negative value disables the autosuspend delay
            echo -1 > "$device_path/power/autosuspend_delay_ms" 2>/dev/null || true
            # 'on' means the device is allowed to be active (not suspended)
            echo on > "$device_path/power/control" 2>/dev/null || true
        fi
    fi
done

# --- Set USB Host Controller to Max Performance ---
# This ensures the main USB host controllers (xhci_hcd is for USB 3.0)
# do not enter a power-saving state.
echo "⚡ Optimizing USB controller performance..."
for controller in /sys/bus/pci/drivers/xhci_hcd/*/power/control; do
    if [ -f "$controller" ]; then
        echo on > "$controller" 2>/dev/null || true
    fi
done

# --- Set All USB Devices to Max Performance ---
# This is a broader rule to ensure all connected USB devices have power
# management set to 'on' (i.e., not suspended).
echo "🔋 Optimizing USB power management..."
for usb_device in /sys/bus/usb/devices/*/power/control; do
    if [ -f "$usb_device" ]; then
        echo on > "$usb_device" 2>/dev/null || true
    fi
done

# ==============================================================================
# Making Optimizations Persistent
# ==============================================================================

# --- Persist Kernel Parameters ---
# The changes made above are temporary and will be lost on reboot.
# These lines write the settings to a modprobe configuration file, so they
# are applied automatically by the kernel every time the system boots.
echo "⚙️ Setting kernel USB parameters..."
echo 'usbcore.usbfs_memory_mb=32' >> /etc/modprobe.d/usb-performance.conf
echo 'usbcore.autosuspend=-1' >> /etc/modprobe.d/usb-performance.conf

# --- Create UDEV Rules for Automatic Configuration ---
# UDEV is the Linux device manager. These rules are automatically applied
# whenever a device is connected. This is a more robust way to manage device
# settings than a one-time script.
echo "📋 Creating udev rules for camera optimization..."
cat > /etc/udev/rules.d/99-camera-performance.rules << 'EOF'
# Rule 1: Disable autosuspend for any USB device that is a video device (class 0e)
SUBSYSTEM=="usb", ATTR{idClass}=="0e", ATTR{power/control}="on"
# Rule 2 & 3: Also disable autosuspend for any device with "Camera" in its name
SUBSYSTEM=="usb", ATTR{product}=="*Camera*", ATTR{power/control}="on"
SUBSYSTEM=="usb", ATTR{product}=="*camera*", ATTR{power/control}="on"

# Rule 4: For video devices (/dev/video*), ensure power management is off
SUBSYSTEM=="video4linux", KERNEL=="video*", ATTR{power/control}="on"
# Rule 5: Set permissions so users in the 'video' group can access the camera
SUBSYSTEM=="video4linux", KERNEL=="video*", MODE="0666", GROUP="video"
EOF

# --- Reload UDEV Rules ---
# Apply the new rules immediately without needing to reboot.
udevadm control --reload-rules
udevadm trigger

# ==============================================================================
# System Performance Optimizations
# ==============================================================================

# --- Set CPU Governor to 'performance' ---
# This forces the CPU to run at its maximum frequency, providing consistent
# performance for real-time tasks like video processing, at the cost of
# higher power consumption.
echo "🔧 Setting CPU frequency scaling for consistent camera performance..."
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [ -f "$cpu" ]; then
        echo performance > "$cpu" 2>/dev/null || true
    fi
done

# --- Set CPU Frequency to Maximum ---
# This explicitly sets the CPU speed to its maximum available frequency.
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_setspeed; do
    if [ -f "$cpu" ]; then
        max_freq=$(cat "$(dirname "$cpu")/scaling_max_freq" 2>/dev/null)
        if [ -n "$max_freq" ]; then
            echo "$max_freq" > "$cpu" 2>/dev/null || true
        fi
    fi
done

# ==============================================================================
# Helper Scripts and Services
# ==============================================================================

# --- Create a Bandwidth Test Script ---
# This creates a convenient helper script that you can run anytime to check
# the camera's performance and see which USB bus it is connected to.
cat > /usr/local/bin/test_camera_bandwidth.sh << 'EOF'
#!/bin/bash
echo "📷 Testing camera bandwidth and performance..."

# Test different resolutions and formats
for device in /dev/video*; do
    if [ -c "$device" ]; then
        echo "Testing device: $device"
        
        # This command attempts to stream 100 frames from the camera
        # It's a quick way to activate the camera for the bandwidth test
        echo "Testing MJPEG formats:"
        v4l2-ctl --device="$device" --set-fmt-video=width=640,height=480,pixelformat=MJPG --stream-mmap --stream-count=100 --stream-to=/dev/null 2>/dev/null
        
        # This command shows the USB device tree, which is the best way
        # to see the speed of the bus (e.g., 480M for USB2, 10000M for USB3)
        echo "USB bandwidth usage:"
        lsusb -t | grep -A5 -B5 "video\|camera\|Camera"
        
        echo "---"
    fi
done
EOF

# Make the new test script executable
chmod +x /usr/local/bin/test_camera_bandwidth.sh

# --- Create a Systemd Service for Persistence ---
# This creates a service that runs on boot to ensure some of the key
# optimizations (like the USB memory buffer) are applied. This is another
# layer of persistence.
cat > /etc/systemd/system/camera-optimization.service << 'EOF'
[Unit]
Description=Camera Performance Optimization
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo 32 > /sys/module/usbcore/parameters/usbfs_memory_mb'
ExecStart=/bin/bash -c 'for dev in /sys/bus/usb/devices/*/power/control; do echo on > "$dev" 2>/dev/null || true; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable the service to make it start on boot
systemctl enable camera-optimization.service

# ==============================================================================
# Completion Summary
# ==============================================================================
echo "✅ Camera bandwidth optimization complete!"
echo ""
echo "📋 Applied optimizations:"
echo "  - Increased USB memory allocation to 32MB"
echo "  - Disabled USB autosuspend for camera devices"
echo "  - Set USB controllers to always-on power mode"
echo "  - Created udev rules for persistent camera optimization"
echo "  - Set CPU to performance mode"
echo "  - Created camera bandwidth testing script"
echo ""
echo "🔄 Please reboot the system for all changes to take effect."
echo "📷 After reboot, test with: /usr/local/bin/test_camera_bandwidth.sh"
echo ""
echo "💡 If FPS is still limited, consider:"
echo "   - Using a shorter USB cable (< 1.5m)"
echo "   - Using a USB 3.0 hub with external power"
echo "   - Reducing resolution to 640x480 or lower"
echo "   - Using a different USB port (preferably USB 3.0)"
