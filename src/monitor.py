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
        logger.debug(f"output_bytes: {output_bytes}")
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
        logger.debug(f"Decoded JSON: {output}")
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
                'jitter':ping.get('jitter', None),
                'latency': ping.get('latency', None)
            },
            'download': {
                'download_speed': convert_bps_to_Mbps(download.get('bandwidth', 0)),
                'latency' : {
                    'iqm': download.get('latency', {}).get('iqm', None),
                    'jitter': download.get('latency', {}).get('jitter', None)
                }
            },
            'upload' : {
                'upload_speed': convert_bps_to_Mbps(upload.get('bandwidth', None)),
                'latency' : {
                    'iqm': upload.get('latency', {}).get('iqm', None),
                    'jitter': upload.get('latency', {}).get('jitter', None)
                }
            },
            'packet_loss': output.get('packetLoss', None),
            'isp': output.get('isp', None),
            'external_ip' : output.get('interface', {}).get('externalIp', None),
            'server' : {
                'name' : server.get('name', None),
                'location' : server.get('location', None)
            }
        }

if __name__ == "__main__":
    internet_speed = run_speedtest()
    print(internet_speed)