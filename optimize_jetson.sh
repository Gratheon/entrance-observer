#!/bin/bash

# Jetson Orin Nano Performance Optimization Script
# This script optimizes system settings for better camera performance

echo "🚀 Optimizing Jetson Orin Nano for entrance-observer performance..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️ This script needs to be run as root for system optimizations"
    echo "Usage: sudo ./optimize_jetson.sh"
    exit 1
fi

# Set CPU governor to performance mode
echo "⚡ Setting CPU governor to performance mode..."
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu3/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu4/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu5/cpufreq/scaling_governor

# Set GPU to maximum performance
echo "🎮 Setting GPU to maximum performance..."
echo 1 > /sys/devices/platform/17000000.ga10b/enable_3d_scaling

# Increase memory bandwidth
echo "💾 Optimizing memory settings..."
echo 1 > /sys/kernel/debug/bpmp/debug/clk/emc/mrq_rate_locked
echo 2133000000 > /sys/kernel/debug/bpmp/debug/clk/emc/rate

# Optimize USB settings for camera
echo "📷 Optimizing USB settings for camera performance..."
# Increase USB buffer sizes
echo 16 > /sys/module/usbcore/parameters/usbfs_memory_mb

# Set fan to maximum (if available)
echo "🌀 Setting fan to maximum speed..."
if [ -f /sys/devices/pwm-fan/target_pwm ]; then
    echo 255 > /sys/devices/pwm-fan/target_pwm
fi

# Disable unnecessary services to free up resources
echo "🛑 Disabling unnecessary services..."
systemctl stop bluetooth
systemctl disable bluetooth
systemctl stop cups
systemctl disable cups

# Optimize network settings
echo "🌐 Optimizing network settings..."
echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_rmem = 4096 87380 134217728' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_wmem = 4096 65536 134217728' >> /etc/sysctl.conf
sysctl -p

# Set process priorities for better real-time performance
echo "⚖️ Optimizing process scheduling..."
echo -1000 > /proc/sys/kernel/sched_rt_runtime_us

# Optimize V4L2 settings
echo "📹 Optimizing V4L2 camera settings..."
# Set video device permissions
chmod 666 /dev/video*

# Create udev rule for camera optimization
cat > /etc/udev/rules.d/99-camera-optimization.rules << EOF
# Optimize camera device settings
SUBSYSTEM=="video4linux", ATTR{name}=="*", RUN+="/bin/chmod 666 %N"
SUBSYSTEM=="video4linux", ATTR{name}=="*", RUN+="/bin/chgrp video %N"
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Create a script to check camera capabilities
cat > /usr/local/bin/check_camera_caps.sh << 'EOF'
#!/bin/bash
echo "📷 Camera Capabilities Check"
echo "=========================="

for device in /dev/video*; do
    if [ -c "$device" ]; then
        echo "Device: $device"
        v4l2-ctl --device=$device --list-formats-ext 2>/dev/null | head -20
        echo "---"
    fi
done
EOF

chmod +x /usr/local/bin/check_camera_caps.sh

# Install v4l-utils if not present
if ! command -v v4l2-ctl &> /dev/null; then
    echo "📦 Installing v4l-utils..."
    apt-get update
    apt-get install -y v4l-utils
fi

echo "✅ Jetson optimization complete!"
echo ""
echo "📋 Summary of optimizations:"
echo "  - CPU governor set to performance mode"
echo "  - GPU set to maximum performance"
echo "  - Memory bandwidth optimized"
echo "  - USB buffer sizes increased"
echo "  - Unnecessary services disabled"
echo "  - Network settings optimized"
echo "  - Camera device permissions set"
echo ""
echo "🔄 Please reboot the system for all changes to take effect."
echo "📷 After reboot, run: /usr/local/bin/check_camera_caps.sh"
echo ""
echo "⚠️ Note: These settings prioritize performance over power efficiency."
