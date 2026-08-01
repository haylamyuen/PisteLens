from typing import List, Tuple
from osm import Piste, fetch_bbox
from rte_ingest import Segment, Point, create_points, process_points


def process(way: Piste) -> Tuple[List[Point], List[Segment]]:
    points = create_points(way.points)
    label = way.name or way.id
    segments = process_points(points, potato=label)

    return points, segments

if __name__ == "__main__":
    # bbox for perisher as ex.
    bbox = (-36.42, 148.38, -36.38, 148.42)

    ways = fetch_bbox(bbox, limit=10)
    print(f"Retrieved {len(ways)} piste ways!")
    print("Processing the first 10 ways...\n")

    results = []
    for way in ways:
        pts, segs = process(way)
        results.append((way, pts, segs))