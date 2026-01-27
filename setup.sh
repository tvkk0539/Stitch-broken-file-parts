#!/bin/bash

# ParFix Web Utility - Bare Metal Setup Script for Debian/Ubuntu
# This script installs all necessary dependencies to run the ParFix Web Utility.

set -e

echo "Starting ParFix Setup..."

# Function to check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup.sh)"
  exit 1
fi

echo "[1/4] Configuring repositories for non-free software (needed for unrar)..."
# Check if using the new debian.sources format (Debian 12+) or old sources.list
if [ -f "/etc/apt/sources.list.d/debian.sources" ]; then
    sed -i -r 's/Components: main/Components: main non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources
elif [ -f "/etc/apt/sources.list" ]; then
    # Backup original
    cp /etc/apt/sources.list /etc/apt/sources.list.bak
    # Add non-free and non-free-firmware if not present
    if ! grep -q "non-free" /etc/apt/sources.list; then
        sed -i '/^deb/ s/$/ non-free non-free-firmware/' /etc/apt/sources.list
    fi
fi

echo "[2/4] Updating package lists and installing dependencies..."
apt-get update
apt-get install -y par2 unrar rar p7zip-full rclone curl python3 python3-pip python3-venv mediainfo ffmpeg

# Verify unrar installation
if unrar | grep -q "unrar-free"; then
    echo "WARNING: It looks like 'unrar-free' was installed instead of the official non-free 'unrar'."
    echo "This script attempts to install the non-free version, but your repo configuration might differ."
    echo "ParFix requires the official RARLAB unrar."
else
    echo "Success: Unrar installed."
fi

echo "[3/4] Installing Python dependencies..."
# Create a virtual environment to avoid polluting system python
python3 -m venv venv
source venv/bin/activate
pip install flask

echo "[4/4] Setup Complete!"
echo ""
echo "To run the application:"
echo "1. source venv/bin/activate"
echo "2. python app.py"
echo ""
echo "Or use the Docker container (Recommended)."
