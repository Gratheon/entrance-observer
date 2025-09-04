import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import telemetry


def test_report_telemetry():
    # video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))

    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")

    metrics_data = {
        "bees_in": 27,
        "bees_out": 15,
        "net_flow": 12,
        "avg_speed_px_per_frame": 1.2,
        "p95_speed_px_per_frame": 3.4,
        "stationary_bees_count": 1
    }

    response = telemetry.report_telemetry(
        metrics_data=metrics_data,
        bearer_token=bearer_token,
        hiveId=hiveId,
        boxId=boxId,
        base_url="https://telemetry.gratheon.com"
    )

    # This is an integration test, so we can't guarantee the response,
    # but we can check that it doesn't raise an exception.
    # A more robust test would mock the server.
    # For now, we'll just check that the function completes.
    pass
