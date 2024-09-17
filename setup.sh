#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# Update package lists
apt-get update

# Install dependencies required by Selenium and Chrome
apt-get install -y wget unzip xvfb libxi6 libgconf-2-4 libnss3 libxss1 libappindicator3-1 libasound2 fonts-liberation libappindicator3-1 xdg-utils

# Download the latest stable version of Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Google Chrome
apt-get install -y ./google-chrome-stable_current_amd64.deb

# Remove the downloaded Chrome package
rm google-chrome-stable_current_amd64.deb

# Verify Chrome installation
google-chrome --version

# Install chromedriver manually to ensure compatibility
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROMEDRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/bin/chromedriver
chmod +x /usr/bin/chromedriver
rm chromedriver_linux64.zip

# Install additional fonts and utilities
apt-get install -y fonts-liberation libappindicator3-1 xdg-utils

echo "Setup completed successfully."
