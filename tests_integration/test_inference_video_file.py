import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import counter

def test_inference_from_video_file_with_UI():
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','tests', 'videos', '314.mp4'))
    beesIn, beesOut = counter.countBees(video_path, display_video=True)
    # todo assert 
    print(f"Bees In: {beesIn}, Bees Out: {beesOut}")
    assert beesIn == 27
    assert beesOut == 15