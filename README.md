# Internet-Speed Monitoring Service

## Setting up python

```
python3 -m venv /opt/internet-speed/venv
```

## Installing speedtest client

```
apt install curl
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
apt install speedtest
```

## Creating logging directory

```
mkdir /var/log/internet-speed
```

## Activating the virtual env

```
source /opt/internet-speed/venv/bin/activate
```

## Creating the user
```
sudo useradd --system --create-home --shell /bin/bash internet-speed --home-dir /opt/internet-speed
```