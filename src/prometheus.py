
from prometheus_client import Gauge, Info, Enum

speedtest_labels = ['server_name', 'server_location']
reachability_labels = ['target', 'protocol']

download_speed = Gauge('download_speed', 'Download speed in Mbps', speedtest_labels, namespace='internet')
download_latency_iqm = Gauge('download_latency_iqm', 'Download latency IQM in ms', speedtest_labels, namespace='internet')
download_latency_jitter = Gauge('download_latency_jitter', 'Download latency jitter in ms', speedtest_labels, namespace='internet')
upload_speed = Gauge('upload_speed', 'Upload speed in Mbps', speedtest_labels, namespace='internet')
upload_latency_iqm = Gauge('upload_latency_iqm', 'Upload latency IQM in ms', speedtest_labels, namespace='internet')
upload_latency_jitter = Gauge('upload_latency_jitter', 'Upload latency jitter in ms', speedtest_labels, namespace='internet')
ping_jitter = Gauge('ping_jitter', 'Ping jitter in ms', speedtest_labels, namespace='internet')
ping_latency = Gauge('ping_latency', 'Ping latency in ms', speedtest_labels, namespace='internet')
packet_loss = Gauge('packet_loss', 'Packet loss', speedtest_labels, namespace='internet')
response_time = Gauge('response_time_ms', 'Response time in ms', reachability_labels, namespace='internet')

info = Info('speedtest_info', 'Other info i.e. ISP and external IP', namespace='internet')

reachability = Enum('reachability', 'Status of reachability', states=['available', 'unavailable'], labels=reachability_labels, namespace='internet')


def collect_speedtest_metrics(speedtest_output):

    if not speedtest_output or not speedtest_output['server'] or not speedtest_output['server']['name'] or not speedtest_output['server']['location']: 
        return

    server_name = speedtest_output['server']['name']
    server_location = speedtest_output['server']['location']

    if speedtest_output['download']['download_speed'] is not None:
        download_speed.labels(server_name, server_location).set(speedtest_output['download']['download_speed'])
    if speedtest_output['download']['latency']['iqm'] is not None:    
        download_latency_iqm.labels(server_name, server_location).set(speedtest_output['download']['latency']['iqm'])
    if speedtest_output['download']['latency']['jitter'] is not None:    
        download_latency_jitter.labels(server_name, server_location).set(speedtest_output['download']['latency']['jitter'])
    if speedtest_output['upload']['upload_speed'] is not None:    
        upload_speed.labels(server_name, server_location).set(speedtest_output['upload']['upload_speed'])
    if speedtest_output['upload']['latency']['iqm'] is not None:    
        upload_latency_iqm.labels(server_name, server_location).set(speedtest_output['upload']['latency']['iqm'])
    if speedtest_output['upload']['latency']['jitter'] is not None:    
        upload_latency_jitter.labels(server_name, server_location).set(speedtest_output['upload']['latency']['jitter'])
    if speedtest_output['ping']['jitter'] is not None:    
        ping_jitter.labels(server_name, server_location).set(speedtest_output['ping']['jitter'])
    if speedtest_output['ping']['latency'] is not None:    
        ping_latency.labels(server_name, server_location).set(speedtest_output['ping']['latency'])
    if speedtest_output['packet_loss'] is not None:    
        packet_loss.labels(server_name, server_location).set(speedtest_output['packet_loss'])

    if (speedtest_output['isp'] is not None and speedtest_output['external_ip'] is not None):
        info.info({'isp': speedtest_output['isp'], 'external_ip': speedtest_output['external_ip']})

def collect_reachability_metrics(http_checks_output, dns_checks_output):

    for domain in http_checks_output:
        target = domain
        protocol = "HTTP"

        if http_checks_output[domain]['response_time_ms'] is not None:
            response_time.labels(target, protocol).set(http_checks_output[domain]['response_time_ms'])
        
        if http_checks_output[domain]['reachable']:
            reachability.labels(target, protocol).state('available')
        else:
            reachability.labels(target, protocol).state('unavailable')

    for domain in dns_checks_output:
        target = domain
        protocol = "DNS"

        if dns_checks_output[domain]['response_time_ms'] is not None:
            response_time.labels(target, protocol).set(dns_checks_output[domain]['response_time_ms'])
        
        if dns_checks_output[domain]['reachable']:
            reachability.labels(target, protocol).state('available')
        else:
            reachability.labels(target, protocol).state('unavailable')