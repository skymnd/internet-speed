import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prometheus import collect_speedtest_metrics, collect_reachability_metrics


class TestCollectSpeedtestMetrics(unittest.TestCase):

    def setUp(self):
        self.patches = []

        self.mock_download_speed = MagicMock()
        self.mock_download_latency_iqm = MagicMock()
        self.mock_download_latency_jitter = MagicMock()
        self.mock_upload_speed = MagicMock()
        self.mock_upload_latency_iqm = MagicMock()
        self.mock_upload_latency_jitter = MagicMock()
        self.mock_ping_jitter = MagicMock()
        self.mock_ping_latency = MagicMock()
        self.mock_packet_loss = MagicMock()
        self.mock_info = MagicMock()

        patches_config = [
            ('prometheus.download_speed', self.mock_download_speed),
            ('prometheus.download_latency_iqm', self.mock_download_latency_iqm),
            ('prometheus.download_latency_jitter', self.mock_download_latency_jitter),
            ('prometheus.upload_speed', self.mock_upload_speed),
            ('prometheus.upload_latency_iqm', self.mock_upload_latency_iqm),
            ('prometheus.upload_latency_jitter', self.mock_upload_latency_jitter),
            ('prometheus.ping_jitter', self.mock_ping_jitter),
            ('prometheus.ping_latency', self.mock_ping_latency),
            ('prometheus.packet_loss', self.mock_packet_loss),
            ('prometheus.info', self.mock_info),
        ]

        for target, mock_obj in patches_config:
            p = patch(target, mock_obj)
            p.start()
            self.patches.append(p)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_collects_all_metrics_with_valid_data(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': 'Test Location'},
            'download': {
                'download_speed': 100.5,
                'latency': {'iqm': 15.0, 'jitter': 2.0}
            },
            'upload': {
                'upload_speed': 50.25,
                'latency': {'iqm': 20.0, 'jitter': 3.0}
            },
            'ping': {'jitter': 1.5, 'latency': 10.0},
            'packet_loss': 0.1,
            'isp': 'Test ISP',
            'external_ip': '1.2.3.4'
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels.assert_called_with('Test Server', 'Test Location')
        self.mock_download_speed.labels().set.assert_called_with(100.5)
        self.mock_upload_speed.labels().set.assert_called_with(50.25)
        self.mock_ping_latency.labels().set.assert_called_with(10.0)
        self.mock_packet_loss.labels().set.assert_called_with(0.1)
        self.mock_info.info.assert_called_with({'isp': 'Test ISP', 'external_ip': '1.2.3.4'})

    def test_returns_early_with_empty_output(self):
        collect_speedtest_metrics({})

        self.mock_download_speed.labels.assert_not_called()

    def test_returns_early_with_none_output(self):
        collect_speedtest_metrics(None)

        self.mock_download_speed.labels.assert_not_called()

    def test_returns_early_with_missing_server(self):
        speedtest_output = {
            'server': None,
            'download': {'download_speed': 100},
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels.assert_not_called()

    def test_returns_early_with_missing_server_name(self):
        speedtest_output = {
            'server': {'name': None, 'location': 'Test Location'},
            'download': {'download_speed': 100},
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels.assert_not_called()

    def test_returns_early_with_missing_server_location(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': None},
            'download': {'download_speed': 100},
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels.assert_not_called()

    def test_skips_none_download_speed(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': 'Test Location'},
            'download': {
                'download_speed': None,
                'latency': {'iqm': 15.0, 'jitter': 2.0}
            },
            'upload': {'upload_speed': 50, 'latency': {'iqm': 20.0, 'jitter': 3.0}},
            'ping': {'jitter': 1.5, 'latency': 10.0},
            'packet_loss': 0.1,
            'isp': 'Test ISP',
            'external_ip': '1.2.3.4'
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels().set.assert_not_called()
        self.mock_upload_speed.labels().set.assert_called_with(50)

    def test_skips_none_latency_values(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': 'Test Location'},
            'download': {
                'download_speed': 100,
                'latency': {'iqm': None, 'jitter': None}
            },
            'upload': {'upload_speed': 50, 'latency': {'iqm': None, 'jitter': None}},
            'ping': {'jitter': None, 'latency': None},
            'packet_loss': None,
            'isp': None,
            'external_ip': None
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_download_speed.labels().set.assert_called_with(100)
        self.mock_download_latency_iqm.labels().set.assert_not_called()
        self.mock_ping_latency.labels().set.assert_not_called()
        self.mock_info.info.assert_not_called()

    def test_skips_info_when_isp_is_none(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': 'Test Location'},
            'download': {'download_speed': 100, 'latency': {'iqm': 15, 'jitter': 2}},
            'upload': {'upload_speed': 50, 'latency': {'iqm': 20, 'jitter': 3}},
            'ping': {'jitter': 1.5, 'latency': 10},
            'packet_loss': 0.1,
            'isp': None,
            'external_ip': '1.2.3.4'
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_info.info.assert_not_called()

    def test_skips_info_when_external_ip_is_none(self):
        speedtest_output = {
            'server': {'name': 'Test Server', 'location': 'Test Location'},
            'download': {'download_speed': 100, 'latency': {'iqm': 15, 'jitter': 2}},
            'upload': {'upload_speed': 50, 'latency': {'iqm': 20, 'jitter': 3}},
            'ping': {'jitter': 1.5, 'latency': 10},
            'packet_loss': 0.1,
            'isp': 'Test ISP',
            'external_ip': None
        }

        collect_speedtest_metrics(speedtest_output)

        self.mock_info.info.assert_not_called()


class TestCollectReachabilityMetrics(unittest.TestCase):

    def setUp(self):
        self.patches = []

        self.mock_response_time = MagicMock()
        self.mock_reachability = MagicMock()

        patches_config = [
            ('prometheus.response_time', self.mock_response_time),
            ('prometheus.reachability', self.mock_reachability),
        ]

        for target, mock_obj in patches_config:
            p = patch(target, mock_obj)
            p.start()
            self.patches.append(p)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_collects_metrics_for_reachable_target(self):
        checks = {
            'example.com': {'reachable': True, 'response_time_ms': 150.5}
        }

        collect_reachability_metrics('HTTP', checks)

        self.mock_response_time.labels.assert_called_with('example.com', 'HTTP')
        self.mock_response_time.labels().set.assert_called_with(150.5)
        self.mock_reachability.labels.assert_called_with('example.com', 'HTTP')
        self.mock_reachability.labels().state.assert_called_with('available')

    def test_collects_metrics_for_unreachable_target(self):
        checks = {
            'example.com': {'reachable': False, 'response_time_ms': None}
        }

        collect_reachability_metrics('HTTP', checks)

        self.mock_response_time.labels().set.assert_not_called()
        self.mock_reachability.labels().state.assert_called_with('unavailable')

    def test_uses_provided_protocol(self):
        checks = {
            '8.8.8.8': {'reachable': True, 'response_time_ms': 25.3}
        }

        collect_reachability_metrics('DNS', checks)

        self.mock_reachability.labels.assert_called_with('8.8.8.8', 'DNS')

    def test_collects_metrics_for_multiple_targets(self):
        checks = {
            'example.com': {'reachable': True, 'response_time_ms': 100},
            'test.com': {'reachable': False, 'response_time_ms': None},
            'foo.com': {'reachable': True, 'response_time_ms': 200}
        }

        collect_reachability_metrics('HTTP', checks)

        self.assertEqual(self.mock_reachability.labels.call_count, 3)

    def test_handles_empty_checks(self):
        collect_reachability_metrics('HTTP', {})

        self.mock_response_time.labels.assert_not_called()
        self.mock_reachability.labels.assert_not_called()


if __name__ == '__main__':
    unittest.main()
