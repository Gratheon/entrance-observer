import numpy as np

def calculate_derived_metrics(track_history, stationary_threshold=10):
    """
    Calculates derived metrics from the track history of bees.

    Args:
        track_history (defaultdict(list)): A dictionary where keys are track_ids and
                                           values are lists of (x, y) coordinates.
        stationary_threshold (int): The maximum distance a bee can move to be
                                    considered stationary.

    Returns:
        dict: A dictionary containing the calculated secondary metrics.
    """
    if not track_history:
        return {
            "avg_speed_px_per_frame": 0,
            "p95_speed_px_per_frame": 0,
            "stationary_bees_count": 0
        }

    bee_speeds = []
    stationary_bees_count = 0
    total_distances = []

    for track_id, track in track_history.items():
        if len(track) > 1:
            distances = [np.linalg.norm(np.array(track[i+1]) - np.array(track[i])) for i in range(len(track)-1)]
            total_distance = sum(distances)
            total_distances.append(total_distance)
            avg_speed = total_distance / (len(track) -1)
            bee_speeds.append(avg_speed)

            if total_distance < stationary_threshold:
                stationary_bees_count += 1

    if not bee_speeds:
        return {
            "avg_speed_px_per_frame": 0,
            "p95_speed_px_per_frame": 0,
            "stationary_bees_count": stationary_bees_count
        }

    avg_speed_px_per_frame = float(np.mean(bee_speeds))
    p95_speed_px_per_frame = float(np.percentile(bee_speeds, 95))

    return {
        "avg_speed_px_per_frame": round(avg_speed_px_per_frame, 2),
        "p95_speed_px_per_frame": round(p95_speed_px_per_frame, 2),
        "stationary_bees_count": stationary_bees_count
    }
