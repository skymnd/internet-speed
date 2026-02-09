# Internet-Speed Monitoring Service

A Python service that monitors internet speed and connectivity,
exposing metrics via Prometheus on port 8000.
This service was mostly created so that my Dad would stop
asking me if I broke the WiFi.

Note: Prometheus and Grafana are not included with this service but the Grafana dashboard JSON is.

I am using this on an Ubuntu LXC on Proxmox with 1 CPU,
4GB storage and 256MiB RAM, but usage hovers at around 
1.5 GB storage and 65MiB RAM.

## Screenshots

![Dashboard 1](grafana/examples/dashboard1.png)

![Dashboard 2](grafana/examples/dashboard2.png)

## Features

- Runs Ookla speedtest every 15 minutes
- Checks HTTP/DNS reachability every 5 minutes
- Exposes Prometheus metrics on port 8000
- Includes Grafana dashboard

## Quick Install

Read through `install/install.sh` and ensure you
understand what the script is doing.
As below, set any environment variables you may
want, and then take and run the install script.
```bash
# Set optional env vars (or use defaults)
export LOGS_FILE_PATH="/var/log/internet-speed/internet-speed.log"
export HTTP_DOMAINS="bbc.co.uk,google.co.uk,apple.com"
export DNS_DOMAINS="1.1.1.1,8.8.8.8"

# Add relevant parts (or all) of install.sh
nano install.sh

# Make executable
sudo chmod +x install.sh

# Run installer
./install.sh
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGS_FILE_PATH` | `/var/log/internet-speed/internet-speed.log` | Log file location |
| `HTTP_DOMAINS` | `bbc.co.uk,google.co.uk,apple.com` | Comma-separated domains for HTTP reachability checks |
| `DNS_DOMAINS` | `1.1.1.1,8.8.8.8` | Comma-separated IPs for DNS reachability checks |

## Manual Installation

Read `install/install.sh` and take the relevant commands.

## Speedtest CLI
See [here](https://www.speedtest.net/apps/cli) for the
speedtest CLI.
To use this, you will have to accept their license
and GDPR agreement.
This is handled in the python script.

## Prometheus Setup

Add to your 
[Prometheus](https://prometheus.io/docs/introduction/overview/)
config:
```yaml
scrape_configs:
  - job_name: 'internet-speed'
    static_configs:
      - targets: ['<SERVICE-IP|localhost>:8000']
```

## Grafana Dashboard

Import the dashboard using `grafana/dashboard.json`.
