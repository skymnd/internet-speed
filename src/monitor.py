import logging
from logging.handlers import RotatingFileHandler
from json import loads as jsonload, JSONDecodeError
from subprocess import run, TimeoutExpired, CalledProcessError

log_filename = '/var/log/internet-speed/internet-speed.log'

logger = logging.getLogger('internet-speed')
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    filename=log_filename,
    encoding='utf-8',
    maxBytes=10*1024*1024, #10 MB
    backupCount=3
)
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Converts b/s to Mb/s
def convert_bps_to_Mbps(bytes_per_second):
    return bytes_per_second / 125000

def run_speedtest():
    try:
        logger.info('Running speed test...')
        output_bytes = run(
                ["speedtest", "--format=json", "--server-id=23968,40628,72004"], 
                capture_output=True,
                timeout=60,
                check=True
            ).stdout
    except TimeoutExpired:
        logger.error("Speedtest took too long.")
        return {}
    except CalledProcessError as err:
        logger.error("Speedtest failed.")
        logger.error(err.stderr)
        return {}
    logger.info('Speed test succeeded.')
    
    logger.info('Starting data processing...')
    try:
        output = jsonload(output_bytes.decode('utf-8'))
    except JSONDecodeError:
        logger.error("Failed to parse speedtest output")
        return {}

    timestamp = output.get('timestamp', 0)
    if (timestamp == 0):
        logger.error("Timestamp can't be 0.")
        raise Exception()
    ping = output.get('ping', {})
    download = output.get('download', {})
    upload = output.get('upload', {})
    server = output.get('server', {})
    return {
            'timestamp' : timestamp,
            'ping': {
                'jitter':ping.get('jitter', 100),
                'latency': ping.get('latency', 100)
            },
            'download': {
                'download_speed': convert_bps_to_Mbps(download.get('bandwidth', 0)),
                'latency' : {
                    'iqm': download.get('latency', {}).get('iqm', 100),
                    'jitter': download.get('latency', {}).get('jitter', 100)
                }
            },
            'upload' : {
                'upload_speed': convert_bps_to_Mbps(upload.get('bandwidth', 100)),
                'latency' : {
                    'iqm': upload.get('latency', {}).get('iqm', 100),
                    'jitter': upload.get('latency', {}).get('jitter', 100)
                }
            },
            'packet_loss': output.get('packetLoss', 0),
            'isp': output.get('isp', ""),
            'external_ip' : output.get('interface', {}).get('externalIp', "X.X.X.X"),
            'server' : {
                'name' : server.get('name', 'unknown'),
                'location' : server.get('location', 'unknown')
            }
        }

if __name__ == "__main__":
    internet_speed = run_speedtest()
    logger.info(f"Download: {internet_speed.get('download', 0)} Mb/s")
    logger.info(f"Upload: {internet_speed.get('upload', 0)} Mb/s")
    print(internet_speed)