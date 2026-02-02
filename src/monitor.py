import logging
from logging.handlers import RotatingFileHandler
from json import loads as jsonload, JSONDecodeError
from math import floor
from subprocess import run, TimeoutExpired
from socket import create_connection
from time import perf_counter_ns
from requests import get as http_get, Timeout

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
    except Exception as err:
        logger.error("Speedtest failed.")
        logger.error(err.stderr)
        return {}
    logger.info('Speedtest subprocess succeeded.')
    
    logger.info('Starting data processing...')
    try:
        output = jsonload(output_bytes.decode('utf-8'))
        logger.debug(f"Decoded JSON: {output}")
    except JSONDecodeError:
        logger.error("Failed to parse speedtest output")
        return {}

    ping = output.get('ping', {})
    download = output.get('download', {})
    upload = output.get('upload', {})
    server = output.get('server', {})
    logger.info('Finished speedtest.')
    return {
            'timestamp' : output.get('timestamp', None),
            'ping': {
                'jitter': ping.get('jitter', None),
                'latency': ping.get('latency', None)
            },
            'download': {
                'download_speed': convert_bps_to_Mbps(download.get('bandwidth', None)),
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

# Takes in a comma separated list of domains e.g.
# "bbc.co.uk,google.co.uk,apple.com"
def run_http_reachability_checks(domains):
    logger.info('Starting HTTP reachability checks...')
    domain_checks = {}
    for domain in domains.split(','):
        domain = domain.strip()
        logger.debug(f"Domain: {domain}")
        try:
            start_time = perf_counter_ns()
            response = http_get(f"https://{domain}", timeout=3)
            response_time = perf_counter_ns() - start_time
            logger.debug(f"Response for {domain}: {response}")
        except Timeout:
            logger.error(f"Request timed out for {domain}.")
            domain_checks[domain] = {
                'reachable': False,
                'response_time_ms': None
            }
            continue
        except Exception as err:
            logger.error(f"Request failed for {domain}.")
            logger.error(err)
            domain_checks[domain] = {
                'reachable': False,
                'response_time_ms': None
            }
            continue
        domain_checks[domain] = {
            'reachable': 200 <= response.status_code < 300,
            'response_time_ms': floor(response_time / 1_000) / 1_000
        }
    logger.info('Finished HTTP reachability checks.')
    return domain_checks

# Takes in a comma separated list of IP addresses e.g.
# "1.1.1.1,8.8.8.8,192.168.1.111"
def run_dns_reachability_checks(ip_addrs):
    logger.info('Starting DNS reachability checks...')
    ip_checks = {}
    for ip_addr in ip_addrs.split(','):
        ip_addr = ip_addr.strip()
        logger.debug(f"IP Address: {ip_addr}")
        try:
            start_time = perf_counter_ns()
            response = create_connection((ip_addr, 53), timeout=3)
            response_time = perf_counter_ns() - start_time
            response.close()
            logger.debug(f"Response: {response}")
        except TimeoutError:
            logger.error(f"Request timed out for {ip_addr}.")
            ip_checks[ip_addr] = {
                'reachable': False,
                'response_time_ms': None
            }
            continue
        except Exception as err:
            logger.error(f"Request failed for {ip_addr}")
            logger.error(err)
            ip_checks[ip_addr] = {
                'reachable': False,
                'response_time_ms': None
            }
            continue
        ip_checks[ip_addr] = {
                'reachable': True,
                'response_time_ms': floor(response_time / 1_000) / 1_000
            }
    logger.info('Finished DNS reachability checks.')
    return ip_checks


if __name__ == "__main__":
    internet_speed = run_speedtest()
    print(internet_speed)
    http_reachability_checks = run_http_reachability_checks("bbc.co.uk,google.co.uk,apple.com")
    print(http_reachability_checks)
    dns_reachability_checks = run_dns_reachability_checks("1.1.1.1,8.8.8.8,192.168.1.111")
    print(dns_reachability_checks)