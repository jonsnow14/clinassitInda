from __future__ import annotations

import time
import uuid
from typing import Any

_TRIPS: dict[str, dict[str, Any]] = {}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def start_trip(
    origin: dict[str, float],
    dest: dict[str, float],
    vehicle: dict[str, Any],
    duration_sec: float = 90.0,
    kind: str = "transport",
) -> dict[str, Any]:
    """Initialize a simulated dispatch trip between origin and destination.

    Constructs a polyline route with intermediate waypoints, records start timestamp,
    stores trip state in memory, and returns initial tracking state.

    Args:
        origin: Dict with "lat" and "lng" keys for starting location.
        dest: Dict with "lat" and "lng" keys for destination location.
        vehicle: Vehicle metadata details dict.
        duration_sec: Total trip duration in seconds. Defaults to 90.0.
        kind: Category type of transport ("transport", "courier", etc.). Defaults to "transport".

    Returns:
        Dictionary containing tracking progress, current coordinates, and trip status.
    """
    trip_id = str(uuid.uuid4())
    waypoints = [
        origin,
        {
            "lat": _lerp(origin["lat"], dest["lat"], 0.35),
            "lng": _lerp(origin["lng"], dest["lng"], 0.28),
        },
        {
            "lat": _lerp(origin["lat"], dest["lat"], 0.7),
            "lng": _lerp(origin["lng"], dest["lng"], 0.72),
        },
        dest,
    ]
    trip = {
        "trip_id": trip_id,
        "kind": kind,
        "vehicle": vehicle,
        "polyline": waypoints,
        "start_ts": time.time(),
        "duration_sec": duration_sec,
        "status": "enroute",
        "dest": dest,
    }
    _TRIPS[trip_id] = trip
    return track(trip_id)


def track(trip_id: str) -> dict[str, Any]:
    """Fetch current location, ETA, and progress status of an active simulated trip.

    Args:
        trip_id: Unique identifier string for the trip.

    Returns:
        Dictionary containing current coordinates, ETA in minutes, progress ratio, and status.

    Raises:
        KeyError: If trip_id does not exist in memory.
    """
    trip = _TRIPS.get(trip_id)
    if not trip:
        raise KeyError(trip_id)
    elapsed = time.time() - trip["start_ts"]
    t = min(1.0, max(0.0, elapsed / trip["duration_sec"]))
    pts = trip["polyline"]
    nseg = len(pts) - 1
    f = t * nseg
    i = min(nseg - 1, int(f))
    local = f - i
    lat = _lerp(pts[i]["lat"], pts[i + 1]["lat"], local)
    lng = _lerp(pts[i]["lng"], pts[i + 1]["lng"], local)
    status = "arrived" if t >= 1 else "enroute"
    trip["status"] = status
    remaining = max(0, int((1 - t) * trip["duration_sec"] / 60))
    return {
        "trip_id": trip_id,
        "kind": trip["kind"],
        "vehicle": trip["vehicle"],
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "eta_min": remaining,
        "status": status,
        "polyline": pts,
        "progress": round(t, 3),
    }
