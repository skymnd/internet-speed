#!/bin/bash

set -e

# Set default env vars. 
# (can be overridden here or by setting them 
# before running the script)
LOGS_FILE_PATH="${LOGS_FILE_PATH:-/var/log/internet-speed/internet-speed.log}"
HTTP_DOMAINS="${HTTP_DOMAINS:-bbc.co.uk,google.co.uk,apple.com}"
DNS_DOMAINS="${DNS_DOMAINS:-1.1.1.1,8.8.8.8}"

# Extract log directory from log file path
LOGS_DIR=$(dirname "$LOGS_FILE_PATH")

echo "Installing internet-speed monitor..."

echo "Installing dependencies..."
sudo apt update
sudo apt install -y curl

echo "Installing Ookla speedtest CLI..."
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt install -y speedtest

echo "Cloning repository..."
cd /tmp
git clone $REPO_URL internet-speed-repo

echo "Creating internet-speed user..."
sudo useradd --system --create-home --home-dir /opt/internet-speed --shell /bin/bash internet-speed

echo "Copying files to /opt/internet-speed..."
sudo cp -r /tmp/internet-speed-repo/. /opt/internet-speed/
sudo rm -rf /tmp/internet-speed-repo
sudo chown -R internet-speed:internet-speed /opt/internet-speed

echo "Setting up Python virtual environment..."
cd /opt/internet-speed
sudo -u internet-speed python3 -m venv venv
sudo -u internet-speed /opt/internet-speed/venv/bin/pip install -r /opt/internet-speed/requirements.txt

echo "Creating log directory at $LOGS_DIR..."
sudo mkdir -p "$LOGS_DIR"
sudo chown internet-speed:internet-speed "$LOGS_DIR"

echo "Creating .env file..."
sudo -u internet-speed touch /opt/internet-speed/.env
echo "LOGS_FILE_PATH=$LOGS_FILE_PATH" | sudo tee -a /opt/internet-speed/.env > /dev/null
echo "HTTP_DOMAINS=$HTTP_DOMAINS" | sudo tee -a /opt/internet-speed/.env > /dev/null
echo "DNS_DOMAINS=$DNS_DOMAINS" | sudo tee -a /opt/internet-speed/.env > /dev/null

echo "Installing systemd service..."
sudo cp /opt/internet-speed/systemd/internet-speed.service.template /etc/systemd/system/internet-speed.service

echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable internet-speed
sudo systemctl start internet-speed

echo "Installation complete!"
