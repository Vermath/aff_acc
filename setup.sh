#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e
set -x  # Enable debugging

echo "Updating package lists..."
apt-get update

echo "Installing dependencies required by Selenium and Chromium..."
apt-get install -y wget unzip xvfb libxi6 libgconf-2-4 libnss3 libxss1 \
    libappindicator3-1 libasound2 fonts-liberation xdg-utils

echo "Installing Chromium and Chromium Driver..."
apt-get install -y chromium chromium-driver

echo "Verifying Chromium installation..."
chromium --version

echo "Verifying Chromium Driver installation..."
chromium-driver --version

echo "Creating Chromium Driver symlink in the correct user directory..."
RUNNING_USER=$(whoami)
CHROMIUM_DRIVER_VERSION=$(chromium-driver --version | grep -oP '\d+\.\d+\.\d+')
EXPECTED_CHROMIUM_DRIVER_PATH="/home/${RUNNING_USER}/.cache/selenium/chromedriver/linux64/${CHROMIUM_DRIVER_VERSION}/chromedriver"

mkdir -p "$(dirname "$EXPECTED_CHROMIUM_DRIVER_PATH")"
ln -sf /usr/bin/chromium-driver "$EXPECTED_CHROMIUM_DRIVER_PATH"

echo "Setup completed successfully."
