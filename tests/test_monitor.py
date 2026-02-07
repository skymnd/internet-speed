import unittest
from unittest.mock import patch, MagicMock
from subprocess import TimeoutExpired
from json import dumps as json_dumps
from requests import Timeout
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from monitor import convert_bps_to_Mbps, run_speedtest, run_http_reachability_checks, run_dns_reachability_checks


class TestConvertBpsToMbps(unittest.TestCase):

    def test_converts_zero(self):
        result = convert_bps_to_Mbps(0)
        self.assertEqual(result, 0)

    def test_converts_125000_to_1_mbps(self):
        result = convert_bps_to_Mbps(125000)
        self.assertEqual(result, 1)

    def test_converts_1250000_to_10_mbps(self):
        result = convert_bps_to_Mbps(1250000)
        self.assertEqual(result, 10)

    def test_converts_12500000_to_100_mbps(self):
        result = convert_bps_to_Mbps(12500000)
        self.assertEqual(result, 100)

    def test_converts_fractional_values(self):
        result = convert_bps_to_Mbps(62500)
        self.assertEqual(result, 0.5)


class TestRunSpeedtest(unittest.TestCase):

    @patch('monitor.run')
    def test_successful_speedtest(self, mock_run):
        mock_output = {
            'timestamp': '2024-01-01T12:00:00Z',
            'ping': {'jitter': 1.5, 'latency': 10.2},
            'download': {
                'bandwidth': 12500000,
                'latency': {'iqm': 15.0, 'jitter': 2.0}
            },
            'upload': {
                'bandwidth': 6250000,
                'latency': {'iqm': 20.0, 'jitter': 3.0}
            },
            'packetLoss': 0.5,
            'isp': 'Test ISP',
            'interface': {'externalIp': '1.2.3.4'},
            'server': {'name': 'Test Server', 'location': 'Test Location'}
        }
        mock_run.return_value = MagicMock(
            stdout=json_dumps(mock_output).encode()
        )

        result = run_speedtest()

        self.assertEqual(result['timestamp'], '2024-01-01T12:00:00Z')
        self.assertEqual(result['ping']['jitter'], 1.5)
        self.assertEqual(result['ping']['latency'], 10.2)
        self.assertEqual(result['download']['download_speed'], 100)
        self.assertEqual(result['download']['latency']['iqm'], 15.0)
        self.assertEqual(result['upload']['upload_speed'], 50)
        self.assertEqual(result['packet_loss'], 0.5)
        self.assertEqual(result['isp'], 'Test ISP')
        self.assertEqual(result['external_ip'], '1.2.3.4')
        self.assertEqual(result['server']['name'], 'Test Server')
        self.assertEqual(result['server']['location'], 'Test Location')

    @patch('monitor.run')
    def test_speedtest_timeout(self, mock_run):
        mock_run.side_effect = TimeoutExpired(cmd='speedtest', timeout=60)

        result = run_speedtest()

        self.assertEqual(result, {})

    @patch('monitor.run')
    def test_speedtest_general_exception(self, mock_run):
        mock_exception = Exception("Command failed")
        mock_exception.stderr = "Error details"
        mock_run.side_effect = mock_exception

        result = run_speedtest()

        self.assertEqual(result, {})

    @patch('monitor.run')
    def test_speedtest_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(stdout=b'not valid json')

        result = run_speedtest()

        self.assertEqual(result, {})

    @patch('monitor.run')
    def test_speedtest_missing_optional_fields(self, mock_run):
        mock_output = {
            'ping': {},
            'download': {'bandwidth': 12500000, 'latency': {}},
            'upload': {'bandwidth': 6250000, 'latency': {}},
            'server': {'name': 'Test Server', 'location': 'Test Location'}
        }
        mock_run.return_value = MagicMock(
            stdout=json_dumps(mock_output).encode()
        )

        result = run_speedtest()

        self.assertIsNone(result['timestamp'])
        self.assertIsNone(result['ping']['jitter'])
        self.assertIsNone(result['ping']['latency'])
        self.assertIsNone(result['packet_loss'])
        self.assertEqual(result['download']['download_speed'], 100)
        self.assertIsNone(result['download']['latency']['iqm'])

    @patch('monitor.run')
    def test_speedtest_missing_server_returns_early(self, mock_run):
        mock_output = {
            'ping': {'jitter': 1.5},
            'download': {'bandwidth': 12500000},
            'upload': {'bandwidth': 6250000},
            'server': {}
        }
        mock_run.return_value = MagicMock(
            stdout=json_dumps(mock_output).encode()
        )

        result = run_speedtest()

        self.assertIsNone(result)


class TestRunHttpReachabilityChecks(unittest.TestCase):

    @patch('monitor.http_get')
    def test_single_domain_reachable(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("example.com")

        self.assertTrue(result['example.com']['reachable'])
        self.assertIsNotNone(result['example.com']['response_time_ms'])

    @patch('monitor.http_get')
    def test_multiple_domains_reachable(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("example.com,test.com,foo.com")

        self.assertEqual(len(result), 3)
        self.assertTrue(result['example.com']['reachable'])
        self.assertTrue(result['test.com']['reachable'])
        self.assertTrue(result['foo.com']['reachable'])

    @patch('monitor.http_get')
    def test_domain_with_whitespace(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("  example.com  , test.com ")

        self.assertIn('example.com', result)
        self.assertIn('test.com', result)

    @patch('monitor.http_get')
    def test_domain_returns_redirect(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("example.com")

        self.assertFalse(result['example.com']['reachable'])

    @patch('monitor.http_get')
    def test_domain_returns_client_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("example.com")

        self.assertFalse(result['example.com']['reachable'])

    @patch('monitor.http_get')
    def test_domain_returns_server_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = run_http_reachability_checks("example.com")

        self.assertFalse(result['example.com']['reachable'])

    @patch('monitor.http_get')
    def test_domain_timeout(self, mock_get):
        mock_get.side_effect = Timeout()

        result = run_http_reachability_checks("example.com")

        self.assertFalse(result['example.com']['reachable'])
        self.assertIsNone(result['example.com']['response_time_ms'])

    @patch('monitor.http_get')
    def test_domain_connection_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        result = run_http_reachability_checks("example.com")

        self.assertFalse(result['example.com']['reachable'])
        self.assertIsNone(result['example.com']['response_time_ms'])

    @patch('monitor.http_get')
    def test_mixed_results(self, mock_get):
        def side_effect(url, **kwargs):
            if 'success.com' in url:
                mock_response = MagicMock()
                mock_response.status_code = 200
                return mock_response
            else:
                raise Exception("Failed")

        mock_get.side_effect = side_effect

        result = run_http_reachability_checks("success.com,failure.com")

        self.assertTrue(result['success.com']['reachable'])
        self.assertFalse(result['failure.com']['reachable'])


class TestRunDnsReachabilityChecks(unittest.TestCase):

    @patch('monitor.create_connection')
    def test_single_ip_reachable(self, mock_connection):
        mock_socket = MagicMock()
        mock_connection.return_value = mock_socket

        result = run_dns_reachability_checks("8.8.8.8")

        self.assertTrue(result['8.8.8.8']['reachable'])
        self.assertIsNotNone(result['8.8.8.8']['response_time_ms'])
        mock_socket.close.assert_called_once()

    @patch('monitor.create_connection')
    def test_multiple_ips_reachable(self, mock_connection):
        mock_socket = MagicMock()
        mock_connection.return_value = mock_socket

        result = run_dns_reachability_checks("8.8.8.8,1.1.1.1,9.9.9.9")

        self.assertEqual(len(result), 3)
        self.assertTrue(result['8.8.8.8']['reachable'])
        self.assertTrue(result['1.1.1.1']['reachable'])
        self.assertTrue(result['9.9.9.9']['reachable'])

    @patch('monitor.create_connection')
    def test_ip_with_whitespace(self, mock_connection):
        mock_socket = MagicMock()
        mock_connection.return_value = mock_socket

        result = run_dns_reachability_checks("  8.8.8.8  , 1.1.1.1 ")

        self.assertIn('8.8.8.8', result)
        self.assertIn('1.1.1.1', result)

    @patch('monitor.create_connection')
    def test_ip_timeout(self, mock_connection):
        mock_connection.side_effect = TimeoutError()

        result = run_dns_reachability_checks("8.8.8.8")

        self.assertFalse(result['8.8.8.8']['reachable'])
        self.assertIsNone(result['8.8.8.8']['response_time_ms'])

    @patch('monitor.create_connection')
    def test_ip_connection_error(self, mock_connection):
        mock_connection.side_effect = Exception("Connection refused")

        result = run_dns_reachability_checks("8.8.8.8")

        self.assertFalse(result['8.8.8.8']['reachable'])
        self.assertIsNone(result['8.8.8.8']['response_time_ms'])

    @patch('monitor.create_connection')
    def test_mixed_results(self, mock_connection):
        def side_effect(address, **kwargs):
            ip, port = address
            if ip == '8.8.8.8':
                return MagicMock()
            else:
                raise Exception("Failed")

        mock_connection.side_effect = side_effect

        result = run_dns_reachability_checks("8.8.8.8,192.168.1.1")

        self.assertTrue(result['8.8.8.8']['reachable'])
        self.assertFalse(result['192.168.1.1']['reachable'])

    @patch('monitor.create_connection')
    def test_connects_to_port_53(self, mock_connection):
        mock_socket = MagicMock()
        mock_connection.return_value = mock_socket

        run_dns_reachability_checks("8.8.8.8")

        mock_connection.assert_called_once_with(('8.8.8.8', 53), timeout=3)


if __name__ == '__main__':
    unittest.main()
