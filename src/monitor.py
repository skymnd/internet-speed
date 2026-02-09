import logging
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from os import path, getenv
from json import loads as jsonload, JSONDecodeError
from subprocess import run, TimeoutExpired
from socket import create_connection
from time import perf_counter, sleep
from requests import get as http_get, Timeout
from prometheus_client import start_http_server, Gauge

from prometheus import collect_speedtest_metrics, collect_reachability_metrics

load_dotenv()

log_filename = getenv("LOGS_FILE_PATH" ,'/var/log/internet-speed/internet-speed.log')
http_domains = getenv("HTTP_DOMAINS", "bbc.co.uk,google.co.uk,apple.com")
dns_domains = getenv("DNS_DOMAINS", "1.1.1.1,8.8.8.8")

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

speedtest_duration_milliseconds = Gauge('speedtest_duration_milliseconds', 'Time taken to run speedtest in ms')
http_check_duration_milliseconds = Gauge('http_check_duration_milliseconds', 'Time taken to run HTTP checks in ms')
dns_check_duration_milliseconds = Gauge('dns_check_duration_milliseconds', 'Time taken to run DNS checks in ms')

# Converts b/s to Mb/s
def convert_bps_to_Mbps(bytes_per_second):
    return bytes_per_second / 125000

def run_speedtest():
    run_args = ["speedtest", "--format=json", "--server-id=23968,40628,72004"]
    if (not path.exists('../.config/ookla/speedtest-cli.json')):
        run_args += ["--accept-license", "--accept-gdpr"]
    try:
        logger.info('Running speed test...')
        output_bytes = run(
                run_args, 
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
                'download_speed': convert_bps_to_Mbps(download.get('bandwidth')) if download.get('bandwidth') is not None else None,
                'latency' : {
                    'iqm': download.get('latency', {}).get('iqm', None),
                    'jitter': download.get('latency', {}).get('jitter', None)
                }
            },
            'upload' : {
                'upload_speed': convert_bps_to_Mbps(upload.get('bandwidth')) if upload.get('bandwidth') is not None else None,
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
            start_time = perf_counter()
            response = http_get(f"https://{domain}", timeout=3)
            response_time = perf_counter() - start_time
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
            'response_time_ms': response_time * 1_000
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
            start_time = perf_counter()
            response = create_connection((ip_addr, 53), timeout=3)
            response_time = perf_counter() - start_time
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
                'response_time_ms': response_time * 1_000
            }
    logger.info('Finished DNS reachability checks.')
    return ip_checks


if __name__ == "__main__":

    start_http_server(8000)

    # Speedtest runs every 3rd iteration (15 min), HTTP/DNS checks run every iteration (5 min)
    i = 0
    while True:
        if i == 0:
            start = perf_counter()
            internet_speed = run_speedtest()
            speedtest_duration_milliseconds.set((perf_counter() - start) * 1_000)
            collect_speedtest_metrics(internet_speed)
        
        http_start = perf_counter()
        http_reachability_checks = run_http_reachability_checks(http_domains)
        http_check_duration_milliseconds.set((perf_counter() - http_start) * 1_000)
        collect_reachability_metrics("HTTP", http_reachability_checks)

        dns_start = perf_counter()
        dns_reachability_checks = run_dns_reachability_checks(dns_domains)
        dns_check_duration_milliseconds.set((perf_counter() - dns_start) * 1_000)
        collect_reachability_metrics("DNS", dns_reachability_checks)

        i += 1
        i = i % 3
        sleep(300)