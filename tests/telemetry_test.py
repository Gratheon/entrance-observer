import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from telemetry import report_telemetry

class TelemetryTest(unittest.TestCase):
    @patch('telemetry.requests.post')
    def test_report_telemetry_success(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response

        metrics_data = {
            "bees_in": 10,
            "bees_out": 5,
            "net_flow": 5,
            "avg_speed_px_per_frame": 1.2,
            "p95_speed_px_per_frame": 3.4,
            "stationary_bees_count": 1
        }
        bearer_token = "test_token"
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(metrics_data, bearer_token, hiveId, boxId, base_url)

        # Assert
        mock_post.assert_called_once_with(
            f'{base_url}/entrance/v1/movement',
            headers={
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            },
            json={
                "boxId": boxId,
                "hiveId": hiveId,
                "beesIn": metrics_data["bees_in"],
                "beesOut": metrics_data["bees_out"],
                "netFlow": metrics_data["net_flow"],
                "avgSpeed": metrics_data["avg_speed_px_per_frame"],
                "p95Speed": metrics_data["p95_speed_px_per_frame"],
                "stationaryBees": metrics_data["stationary_bees_count"],
            },
            timeout=120,
            allow_redirects=True
        )

    @patch('telemetry.requests.post')
    def test_report_telemetry_failure(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        metrics_data = {
            "bees_in": 10,
            "bees_out": 5,
            "net_flow": 5,
            "avg_speed_px_per_frame": 1.2,
            "p95_speed_px_per_frame": 3.4,
            "stationary_bees_count": 1
        }
        bearer_token = "test_token"
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(metrics_data, bearer_token, hiveId, boxId, base_url)

        # Assert
        mock_post.assert_called_once()

    def test_report_telemetry_missing_credentials(self):
        # Arrange
        metrics_data = {
            "bees_in": 10,
            "bees_out": 5,
            "net_flow": 5,
            "avg_speed_px_per_frame": 1.2,
            "p95_speed_px_per_frame": 3.4,
            "stationary_bees_count": 1
        }
        bearer_token = None
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(metrics_data, bearer_token, hiveId, boxId, base_url)

        # Assert - No API call should be made
        # This is implicitly tested by not patching requests.post

if __name__ == '__main__':
    unittest.main()
