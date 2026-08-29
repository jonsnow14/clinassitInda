from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .paths import PURNIA_DIR

PHC = json.loads((PURNIA_DIR / "phc.json").read_text(encoding="utf-8"))


def load_json(name: str) -> Any:
    """Load and parse a JSON dataset file from the Purnia geo directory.

    Args:
        name: Name of the JSON file within the Purnia data directory.

    Returns:
        Parsed JSON object or collection.
    """
    path: Path = PURNIA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute the great-circle distance between two geographic coordinates.

    Args:
        lat1: Latitude of the starting point in degrees.
        lng1: Longitude of the starting point in degrees.
        lat2: Latitude of the destination point in degrees.
        lng2: Longitude of the destination point in degrees.

    Returns:
        Distance in kilometers between the two coordinates.
    """
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def km_from_phc(lat: float, lng: float) -> float:
    """Calculate distance in kilometers from the base PHC to given coordinates.

    Args:
        lat: Latitude coordinate in degrees.
        lng: Longitude coordinate in degrees.

    Returns:
        Rounded distance in kilometers from the base PHC.
    """
    return round(haversine_km(PHC["lat"], PHC["lng"], lat, lng), 2)
