#!/bin/bash
set -e
set -x  # Enable debugging

echo "Updating package lists..."
apt-get update

echo "Installing dependencies required by Selenium and Chrome..."
apt-get install -y wget unzip xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator3-1 libasound2 fonts-liberation libappindicator3-1 xdg-utils

echo "Downloading the latest stable version of Google Chrome..."
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

echo "Installing Google Chrome..."
apt-get install -y ./google-chrome-stable_current_amd64.deb

echo "Removing the downloaded Chrome package..."
rm google-chrome-stable_current_amd64.deb

echo "Verifying Chrome installation..."
google-chrome --version

echo "Installing Chromedriver..."
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1)
CHROMEDRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_MAJOR_VERSION")
wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver
rm chromedriver_linux64.zip

echo "Creating Chromedriver symlink in the correct user directory..."
RUNNING_USER=$(whoami)
EXPECTED_CHROMEDRIVER_PATH="/home/${RUNNING_USER}/.cache/selenium/chromedriver/linux64/${CHROMEDRIVER_VERSION}/chromedriver"
mkdir -p "$(dirname "$EXPECTED_CHROMEDRIVER_PATH")"
ln -s /usr/bin/chromedriver "$EXPECTED_CHROMEDRIVER_PATH"

echo "Installing additional fonts and utilities..."
apt-get install -y fonts-liberation libappindicator3-1 xdg-utils

echo "Setup completed successfully."
