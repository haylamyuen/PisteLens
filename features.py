import math
from typing import Dict, List, Optional, Union
from rte_ingest import Segment, Point, distance

def compute_feats( points: List[Point], segments: List[Segment], grooming: Optional[str] = "classic") -> Dict[str, Union[float, str, None]]:
    if len(points) < 2:
        raise ValueError("Please make sure there are at least 2 segments provided.") # >= 2 needed for sinuosity

    grades = [s.grade for s in segments]
    abs_grades = [abs(g) for g in grades]
    lens = [s.distance for s in segments]
    totlen = sum(lens)

    if totlen <= 0:
        raise ValueError("Invalid route length.")

    donky = 0
    wonky = 0
    for grade, abs_grade, length in zip(grades, abs_grades, lens):
        donky += grade * length
        wonky += abs_grade * length

    avg_grade = donky / totlen
    avg_abs_grade = wonky / totlen

    # formula from https://www.mathsisfun.com/data/standard-deviation.html
    varsum = 0
    for abs_grade, length in zip(abs_grades, lens):
        diff = abs_grade-avg_abs_grade
        varsum += diff**2 * length

    variance = varsum / totlen
    grade_std = math.sqrt(variance)

    # formula from https://en.wikipedia.org/wiki/Sinuosity
    start, end = points[0], points[-1]
    d_straight = distance(start.lat, start.lon, end.lat, end.lon)
    sinuosity = totlen/ d_straight if d_straight > 0 else float("inf")

    return {
        "length": totlen,
        "avg_grade": avg_grade,
        "avg_abs_grade": avg_abs_grade,
        "max_abs_grade": max(abs_grades),
        "grade_std": grade_std,
        "sinuosity": sinuosity,
        "grooming": grooming
    }
