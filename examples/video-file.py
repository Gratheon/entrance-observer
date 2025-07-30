import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import counter


video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))

beesIn, beesOut = counter.countBees(video_path, display_video=True)