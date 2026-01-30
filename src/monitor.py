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

formatter = logging.Formatter('%(asctime)s %(levelname)s:%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

default = {
    'download': 0,
    'upload': 0
}

# Gets download speed in Mb/s
def get_download_speed(download_info):
    elapsed = download_info.get('elapsed', 0)
    if (elapsed==0):
        return 0
    return download_info.get('bytes', 0)/(elapsed * 125)

# Gets upload speed in Mb/s
def get_upload_speed(upload_info):
    elapsed = upload_info.get('elapsed', 0)
    if (elapsed==0):
        return 0
    return upload_info['bytes']/(upload_info['elapsed'] * 125)

def get_internet_speed():
    try:
        logger.info('Running speed test...')
        output_bytes = run(
                ["speedtest", "--format=json"], 
                capture_output=True,
                timeout=60,
                check=True
            ).stdout
    except TimeoutExpired:
        logger.error("Speedtest took too long.")
        return default
    except CalledProcessError as err:
        logger.error("Speedtest failed.")
        logger.error(err.stderr)
        return default
    logger.info('Speed test succeeded.')
    
    logger.info('Starting data processing...')
    try:
        output = jsonload(output_bytes.decode('utf-8'))
    except JSONDecodeError:
        logger.error("Failed to parse speedtest output")
        return default

    download_speed = get_download_speed(output.get('download', {}))
    upload_speed = get_upload_speed(output.get('upload', {}))
    return {
            'download': download_speed,
            'upload': upload_speed
        }

if __name__ == "__main__":
    internet_speed = get_internet_speed()
    logger.info(f"Download: {internet_speed['download']} Mb/s")
    logger.info(f"Upload: {internet_speed['upload']} Mb/s")