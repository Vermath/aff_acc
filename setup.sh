#!/bin/bash
# Update package lists
apt-get update

# Install dependencies required by Selenium and Chrome
apt-get install -y wget unzip xvfb libxi6 libgconf-2-4

# Download the latest stable version of Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Google Chrome
apt-get install -y ./google-chrome-stable_current_amd64.deb

# Remove the downloaded Chrome package
rm google-chrome-stable_current_amd64.deb

# Verify Chrome installation
google-chrome --version

# Set up chromedriver using selenium-manager (built into Selenium 4.10.0+)
# Selenium should handle chromedriver installation automatically
