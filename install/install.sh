#!/bin/bash

set -e

# Update package lists and install curl
sudo apt update
sudo apt install -y curl

# Use curl to download speedtest setup
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt install -y speedtest

# Clone repo to temporary location
cd /tmp
git clone $REPO_URL internet-speed-repo

# Create user and group
sudo useradd --system --create-home --home-dir /opt/internet-speed --shell /bin/bash internet-speed

# Move repo to final location
sudo cp -r /tmp/internet-speed-repo/. /opt/internet-speed/
sudo rm -rf /tmp/internet-speed-repo
sudo chown -R internet-speed:internet-speed /opt/internet-speed

# Set up Python virtual environment
cd /opt/internet-speed
sudo -u internet-speed python3 -m venv venv
sudo -u internet-speed /opt/internet-speed/venv/bin/pip install -r /opt/internet-speed/requirements.txt

# Create log directory with correct permissions
sudo mkdir -p /var/log/internet-speed
sudo chown internet-speed:internet-speed /var/log/internet-speed

# Copy service to systemd
sudo cp /opt/internet-speed/systemd/internet-speed.service.template /etc/systemd/system/internet-speed.service

# Reload daemon and start service
sudo systemctl daemon-reload
sudo systemctl enable internet-speed
sudo systemctl start internet-speed