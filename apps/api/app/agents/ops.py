from __future__ import annotations

from typing import Any, Literal

from ..geo import PHC, haversine_km, km_from_phc, load_json
from ..simulate import start_trip, track

Need = Literal["icu", "oxygen", "general"]


def list_beds(need: Need = "icu") -> list[dict[str, Any]]:
    hospitals = load_json("hospitals.json")
    key = {"icu": "beds_icu", "oxygen": "beds_oxygen", "general": "beds_general"}[need]

    def sort_key(h: dict[str, Any]) -> tuple:
        km = haversine_km(PHC["lat"], PHC["lng"], h["lat"], h["lng"])
        return (0 if h.get("accepts_nstemi") else 1, -int(h.get(key) or 0), km)

    out = []
    for h in sorted(hospitals, key=sort_key):
        out.append(
            {
                **h,
                "km": km_from_phc(h["lat"], h["lng"]),
                "need": need,
                "need_beds": int(h.get(key) or 0),
            }
        )
    return out


def list_transport(kind: str | None = None) -> list[dict[str, Any]]:
    vehicles = load_json("ambulances.json")
    if kind:
        vehicles = [v for v in vehicles if v["kind"] == kind]
    vehicles = [v for v in vehicles if v.get("available")]
    vehicles.sort(key=lambda v: (0 if v["kind"] == "ambulance" else 1, v.get("eta_min", 99)))
    for v in vehicles:
        v["km"] = km_from_phc(v["lat"], v["lng"])
    return vehicles


def dispatch_transport(kind: str | None = None, need_oxygen: bool = True) -> dict[str, Any]:
    candidates = list_transport(kind)
    if need_oxygen:
        oxy = [v for v in candidates if v.get("oxygen")]
        if oxy:
            candidates = oxy
    if not candidates:
        raise LookupError("No available vehicle")
    vehicle = candidates[0]
    dest = {"lat": PHC["lat"], "lng": PHC["lng"]}
    origin = {"lat": vehicle["lat"], "lng": vehicle["lng"]}
    duration = max(45.0, float(vehicle.get("eta_min") or 10) * 6)
    return start_trip(origin, dest, vehicle, duration_sec=duration, kind="transport")


def track_transport(trip_id: str) -> dict[str, Any]:
    return track(trip_id)
