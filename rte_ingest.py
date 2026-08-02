import glob # so that we can search for any gpx file. like not limited by name
import math
from dataclasses import dataclass
from typing import List, Optional
import gpxpy
import requests

SEG_LEN = 75
SMOOTHER = 3
BATCH_SIZE = 100

# https://www.youtube.com/watch?v=DgFkLJmwOBA
# SELF NOTE: refer back to the video if there are any errors
@dataclass
class Point:
    lat: float
    lon: float
    elev: Optional[float] = 67.6767
    cumdist: float = 0.0

@dataclass
class Segment:
    start_dist: float
    end_dist: float
    distance: float
    elev_change: float
    grade: float


def parse(filepath :str) -> List[Point] :
    with open(filepath, "r") as banana:
        gpx = gpxpy.parse(banana)

    if len(gpx.tracks) != 1:
        raise  ValueError("Please make sure there is exactly one track in the file.")
    track=gpx.tracks[0]

    points = []
    for segment in track.segments:
        for point in segment.points:
            points.append(Point(lat=point.latitude, lon=point.longitude, elev=point.elevation))

    if len(points) == 0:
        raise ValueError("No points found.")

    return points



# i think equirectangular should be ok for this because the distances are very small
# https://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points
def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000 #radius of earth
    lettuce = math.radians((lat1+lat2)/2)
    dx = math.radians(lon2-lon1)*R*math.cos(lettuce)
    dy = math.radians(lat2-lat1)*R
    return math.sqrt(dx**2 + dy**2)

def fetch_elev(batch: List[Point]) -> List[float]:
    # https://github.com/Jorl17/open-elevation/blob/master/docs/api.md
    thingos = [
        ("Open-Elevation", "https://api.open-elevation.com/api/v1/lookup", {"locations": [{"latitude":p.lat, "longitude":p.lon} for p in batch]}),
        ("Open Topo Data", "https://api.opentopodata.org/v1/srtm90m", {"locations": "|".join(f"{p.lat},{p.lon}" for p in batch)})
    ]

    for name, url, json in thingos:
        try:
            response = requests.post(url, json=json, timeout=30)
            response.raise_for_status()

            results = []
            for r in response.json()["results"]:
                results.append(r["elevation"])

            return results
        
        except requests.RequestException:
            print(f"{name} didn't work, trying the next one...")

    raise RuntimeError("Elevation getting failed.")

def fill_elev(points: List[Point] ) -> None:
    missing = [p for p in points if p.elev == 67.6767]
    if not missing:
        return

    for i in range(0, len(missing), BATCH_SIZE):
        batch= missing[i:i + BATCH_SIZE]
        try:
            elevs = fetch_elev(batch)
            for point, elev in zip(batch, elevs):
                point.elev = elev
        except RuntimeError:
            print(f"Couldn't get the elevation data.")
            for point in batch:
                point.elev = 0

 

# smoothing needed cuz raw data is noisey
def smooth(points: List[Point], window: int = SMOOTHER) -> None:
    elevations = [p.elev for p in points] # make copy before smoothing otherwise the smoothed profile will be skewed
    potato = window // 2
    smoothed = []

    # sma used for now, weighted average would probably be better
    for i in range(len(elevations)):
        lo, hi = max(0,i-potato), min(len(elevations),i+potato+1)
        vals = elevations[lo:hi]
        smoothed.append(sum(vals) / len(vals))
    for point, value in zip(points, smoothed):
        point.elev = value



def elev_at(d: float, points: List[Point] ) ->  float:
    for prev, curr in zip(points, points[1:]):
        if prev.cumdist <= d <= curr.cumdist: # safeguard against funky data
            span = curr.cumdist - prev.cumdist
            if span == 0: # protects against duplicate GPS points
                return prev.elev
            
            t = (d-prev.cumdist) / span
            return prev.elev + t*(curr.elev-prev.elev)
    return points[-1].elev

def resample(points: List[Point] , SEG_LEN: float = SEG_LEN) -> List[Segment]:
    totaldist = points[-1].cumdist
    if totaldist <= 0:
        raise ValueError("Invalid distance.")

    cutd = list(range(0, int(totaldist), int(SEG_LEN))) # first time ive used range not in a loop!!
    cutd = [float(c) for c in cutd]
    cutd.append(totaldist)
    cutd = sorted(set(cutd)) # used set to remove duplicates in rare case totaldist lands on grid

    segments = []
    for start_d,  end_d in zip(cutd, cutd[1:]):
        start_elev = elev_at(start_d, points)
        end_elev = elev_at(end_d, points)

        d= end_d-start_d
        if d == 0:
            continue
        
        elev_change = end_elev-start_elev
        grade = elev_change / d

        seg = Segment(
                start_dist=start_d,
                end_dist=end_d,
                distance=d,
                elev_change=elev_change,
                grade=grade)

        segments.append(seg)
    return segments


def process_points(points: List[Point], potato) -> List[Segment] :
    print(f"Processing {potato}...")

    fill_elev(points)

    points[0].cumdist = 0
    for prev, curr in zip(points, points[1:]):
        curr.cumdist = prev.cumdist + distance(prev.lat, prev.lon, curr.lat, curr.lon)
    
    smooth(points)

    dist = points[-1].cumdist/1000
    desc = sum(max(0, prev.elev-curr.elev) for prev, curr in zip(points, points[1:]))
    print(f"  distance={dist:.2f}km, descent={desc:.2f}m")
    segments = resample(points)

    return segments

def create_points(coords: List[tuple]) -> List[Point]:
    if len(coords) == 0:
        raise ValueError("No coordinates :(")
    return [Point(lat=lat, lon=lon, elev=67.6767) for lat, lon in coords]

def process_route(filepath: Optional[str] = "looksie here, we have a fake filepath") -> List[Segment] :
    if filepath == "looksie here, we have a fake filepath":
        matches = glob.glob("*.gpx")
        try:
            filepath = matches[0]
        except IndexError:
            raise FileNotFoundError("No GPX files found")
        
    points= parse(filepath)
    print(f"Successfully parsed the file.")
    
    return process_points(points, potato=filepath)