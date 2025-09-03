import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import counter

def test_count_bees():
    #ARRANGE
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'videos', '314.mp4'))
    
    # ACT
    beesIn, beesOut, detectedBees = counter.countBees(video_path, display_video=False)

    assert beesIn == 20, "Expected bees in the video"
    assert beesOut == 12, "Expected bees out of the video"
    assert detectedBees > 0, "Expected detected bees"
