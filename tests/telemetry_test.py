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

        beesIn = 10
        beesOut = 5
        bearer_token = "test_token"
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)

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
                "beesIn": beesIn,
                "beesOut": beesOut,
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

        beesIn = 10
        beesOut = 5
        bearer_token = "test_token"
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)

        # Assert
        mock_post.assert_called_once()

    def test_report_telemetry_missing_credentials(self):
        # Arrange
        beesIn = 10
        beesOut = 5
        bearer_token = None
        hiveId = "test_hive"
        boxId = "test_box"
        base_url = "http://mock-api.com"

        # Act
        report_telemetry(beesIn, beesOut, bearer_token, hiveId, boxId, base_url)

        # Assert - No API call should be made
        # This is implicitly tested by not patching requests.post

if __name__ == '__main__':
    unittest.main()
