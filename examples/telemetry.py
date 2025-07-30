import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import telemetry


video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))

beesIn, beesOut = telemetry.report_telemetry(
    beesIn=27,  # Example value
    beesOut=15,  # Example value
    bearer_token="your_bearer_token_here",  # Replace with your actual bearer token
    hiveId="68",
    boxId="250",
    base_url="https://telemetry.gratheon.com"
)