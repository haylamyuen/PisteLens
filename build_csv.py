from csv import *
from typing import List, Optional, Tuple
from process_piste import process
from osm import Piste, fetch_bbox
from features import compute_feats



def build_rows(bbox: Tuple[float, float, float, float], resort : str, limit : Optional[int] = None) -> List[dict]:
    ways = fetch_bbox(bbox, limit=limit)
    print(f"Retrieved {len(ways)} piste ways!")

    rows = []
    for way in ways:
        features = []
        try:
            points, segments = process(way)
            features = compute_feats(points, segments, grooming=way.grooming)
        except ValueError:
            continue

        row = {
            "id": way.id,
            "resort": resort,
            "name": way.name or "",
            "difficulty": way.difficulty or "",
            "type": way.type or "",
            **features,
        }
        rows.append(row)

    print(f"Created {len(rows)} rows!")

    return rows


if __name__ == "__main__":

    resorts = {
        "perisher": (-36.42, 148.35, -36.37, 148.45),
        "3-vallees": (45.27, 6.41, 45.47, 6.75),
        "zermatt": (45.85, 7.53, 46.07, 7.85),
        "chamonix": (45.85, 6.78, 45.98, 6.98),
        "thredbo": (-36.51, 148.27, -36.48, 148.32),
        "whistler": (50.04, -123.01, 50.13, -122.86),
        "niseko": (42.82, 140.62, 42.91, 140.74),
        "hakuba": (36.58, 137.74, 36.81, 137.95),
        "aspen": (39.11, -107.00, 39.24, -106.78),
        "vail": (39.53, -106.44, 39.65, -106.26)
    }

    rows = []
    with open("skiruns.csv", "w", newline="") as banana:
        writer = DictWriter(banana, fieldnames=["id", "resort", "name", "difficulty", "type", "length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"])
        writer.writeheader()

    for resort, bbox in resorts.items():
        rows.extend(build_rows(bbox, resort=resort, limit=10000))

        with open("skiruns.csv", "a", newline="") as banana:
            writer = DictWriter(banana, fieldnames=["id", "resort", "name", "difficulty", "type", "length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"])
            writer.writerows(rows)