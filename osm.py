from dataclasses import dataclass
from typing import List, Optional, Tuple
import requests

ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]
HEADER = {"User-Agent": "PisteLens/1.0; https://github.com/haylamyuen/PisteLens"} # https://github.com/drolbr/Overpass-API/issues/791
TIMEOUT = 90

@dataclass
class Piste:
    id: int
    name: Optional[str]
    difficulty: Optional[str]
    type: Optional[str]
    grooming: Optional[str]
    points: List[Tuple[float, float]]


# https://www.youtube.com/watch?v=M_1Sas9l57o
def create_qbbox(bbox: Tuple[float, float, float, float], limit: int = None) -> str:
    south, west, north, east = bbox
    return f"""[out:json][timeout:{TIMEOUT}];
            (way["piste:type"]({south},{west},{north},{east}););
            out geom {limit if limit is not None else ""};"""

def parse(data: dict) -> List[Piste ]:
    ways=  []
    for element in data.get("elements", []):

        geom = element.get("geometry", [])
        if not geom:
            continue

        points = []
        for point in geom:
            points.append((point["lat"], point["lon"]))


        if "tags" in element:
            tags = element["tags"]
        else:
            tags = {}

        piste = Piste(
                id=element["id"],
                name=tags.get("name"),
                difficulty=tags.get("piste:difficulty"),
                type=tags.get("piste:type"),
                grooming=tags.get("piste:grooming") or "classic",
                points=points)
        
        ways.append(piste)

    return ways

def query_op(query: str)  -> dict:
    for endpoint in ENDPOINTS:
        try:
            response = requests.post(endpoint, data={"data": query}, headers=HEADER, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException:
            print(f" {endpoint} failed...")
 
    raise RuntimeError(f"All Overpass endpoints failed.")

def fetch_bbox(bbox: Tuple[float, float, float, float], limit: Optional[int] = None) -> List[Piste] :
    query = create_qbbox(bbox, limit=limit)
    data = query_op(query)
    return parse(data)
