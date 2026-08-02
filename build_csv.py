from csv import DictWriter
from typing import List, Tuple

from process_piste import process
from osm import fetch_bbox
from features import compute_feats

def buildata(bbox: Tuple[float, float, float, float], resort, limit = None) -> List[dict]:
    ways = fetch_bbox(bbox, limit=limit)
    rows = []
    for way in ways:
        features = []
        try:
            points, segments = process(way)
            features = compute_feats(points, segments, grooming=way.grooming)
        except ValueError:
            continue

        row = {"id": way.id, "resort": resort, "name": way.name or "", "difficulty": way.difficulty or "", "type": way.type or "", **features}
        rows.append(row)

    print(f"Created {len(rows)} rows for {resort}.")
    return rows


if __name__ == "__main__":
    # https://tools.mofei.life/bbox
    resorts = {
        #"perisher": (-36.42, 148.35, -36.37, 148.45),
        #"3-vallees": (45.27, 6.41, 45.47, 6.75),
        #"zermatt": (45.85, 7.53, 46.07, 7.85),
        #"chamonix": (45.85, 6.78, 45.98, 6.98),
        #"thredbo": (-36.51, 148.27, -36.48, 148.32),
        #"whistler": (50.04, -123.01, 50.13, -122.86),
        #"niseko": (42.82, 140.62, 42.91, 140.74),
        #"hakuba": (36.58, 137.74, 36.81, 137.95),
        #"aspen": (39.11, -107.00, 39.24, -106.78),
        #"vail": (39.53, -106.44, 39.65, -106.26),
        #"breckenridge": (39.45, -106.05, 39.55, -105.90),
        #"keystone": (39.58, -105.90, 39.68, -105.75),
        "sella-ronda": (46.40, 11.71, 46.60, 11.93),
        "4-vallees": (45.99, 7.10, 46.30, 7.45),
        "big-sky": (45.20, -111.50, 45.32, -111.34),
        "jackson-hole": (43.55, -110.88, 43.65, -110.80),
        "valle-nevado": (-33.37, -70.39, -33.31, -70.14),
        "cardrona": (-44.88, 168.92, -44.85, 168.97),
        "coronet-peak": (-44.93, 168.72, -44.91, 168.76),
        "remarkables": (-45.10, 168.79, -45.00, 168.84)
    }

    seinfields = ["id", "resort", "name", "difficulty", "type", "length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"]
    for res, bb in resorts.items():
        rows = buildata(bb, resort=res, limit=10000)

        with open("data/skiruns.csv", "a", newline="", encoding="utf-8") as banana:
            writer = DictWriter(banana, fieldnames=seinfields)
            if banana.tell() == 0:
                writer.writeheader()
            writer.writerows(rows)