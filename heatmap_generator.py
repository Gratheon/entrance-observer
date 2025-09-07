import json
import numpy as np
import cv2
import argparse
from collections import defaultdict

def generate_heatmap(track_file_path, output_file_path):
    """
    Generates a heatmap from a track history file.

    Args:
        track_file_path (str): The path to the track_history.jsonl file.
        output_file_path (str): The path to save the generated heatmap image.
    """
    try:
        with open(track_file_path, 'r') as f:
            first_line = f.readline()
            if not first_line:
                print("Error: Track history file is empty.")
                return

            data = json.loads(first_line)
            frame_dimensions = data.get("frame_dimensions")
            if not frame_dimensions:
                print("Error: Frame dimensions not found in the first line of the track history file.")
                return
            
            height = frame_dimensions["height"]
            width = frame_dimensions["width"]
            print(f"Frame dimensions: {width}x{height}")
            
            heatmap = np.zeros((height, width), dtype=np.float32)
            total_tracks = 0

            # Process the first line
            track_history = data.get("track_history", {})
            num_tracks = len(track_history)
            total_tracks += num_tracks
            print(f"Found {num_tracks} tracks in the first line.")
            for track_id, track in track_history.items():
                for x, y in track:
                    if 0 <= y < height and 0 <= x < width:
                        heatmap[y, x] += 1

            # Process the rest of the file
            for i, line in enumerate(f, 2):
                try:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    track_history = data.get("track_history", {})
                    num_tracks = len(track_history)
                    total_tracks += num_tracks
                    if num_tracks > 0:
                        print(f"Found {num_tracks} tracks on line {i}.")
                    for track_id, track in track_history.items():
                        for x, y in track:
                            if 0 <= y < height and 0 <= x < width:
                                heatmap[y, x] += 1
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON on line {i}. Skipping.")
                    continue
            
            print(f"Total tracks processed: {total_tracks}")
            print(f"Heatmap min/max before normalization: {np.min(heatmap)}/{np.max(heatmap)}")
                            
    except FileNotFoundError:
        print(f"Error: File not found at {track_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {track_file_path}")
        return

    # Use a logarithmic scale for better visualization
    if np.max(heatmap) > 0:
        heatmap = np.log1p(heatmap)  # log1p is log(1+x) to handle zeros
        heatmap = 255 * (heatmap / np.max(heatmap))
    
    heatmap_img = heatmap.astype(np.uint8)
    
    # Apply a color map
    colored_heatmap = cv2.applyColorMap(heatmap_img, cv2.COLORMAP_HOT)

    cv2.imwrite(output_file_path, colored_heatmap)
    print(f"Heatmap saved to {output_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a heatmap from bee track history.")
    parser.add_argument("track_file", help="Path to the track_history.jsonl file.")
    parser.add_argument("-o", "--output", default="heatmap.png", help="Path to save the output heatmap image.")
    args = parser.parse_args()

    generate_heatmap(args.track_file, args.output)
