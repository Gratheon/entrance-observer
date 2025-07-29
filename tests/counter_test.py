import os
import pytest
import counter

def test_count_bees():
    #ARRANGE
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'videos', '314.mp4'))
    
    # ACT
    beesIn, beesOut = counter.countBees(video_path, display_video=False)

    assert beesIn == 27, "Expected bees in the video"
    assert beesOut == 15, "Expected bees out of the video"
