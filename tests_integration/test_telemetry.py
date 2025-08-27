import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import telemetry


def test_report_telemetry():
    # video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))

    bearer_token = os.getenv("API_TOKEN")
    hiveId = os.getenv("HIVE_ID")
    boxId = os.getenv("SECTION_ID")

    response = telemetry.report_telemetry(
        beesIn=27,  # Example value
        beesOut=15,  # Example value
        bearer_token=bearer_token,  # Replace with your actual bearer token
        hiveId=hiveId,
        boxId=boxId,
        base_url="https://telemetry.gratheon.com"
    )

    assert response == '{"message":"OK"}'