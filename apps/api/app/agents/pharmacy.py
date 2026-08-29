from __future__ import annotations

from typing import Any

from ..geo import PHC, km_from_phc, load_json
from ..simulate import start_trip, track

MED_ALIASES = {
    "aspirin": "aspirin",
    "asa": "aspirin",
    "clopidogrel": "clopidogrel",
    "plavix": "clopidogrel",
    "atorvastatin": "atorvastatin",
    "statin": "atorvastatin",
    "metformin": "metformin",
    "amlodipine": "amlodipine",
    "isosorbide": "isosorbide",
    "gtn": "isosorbide",
}


def _norm_meds(meds: list[str]) -> list[str]:
    out: list[str] = []
    for raw in meds:
        key = MED_ALIASES.get(raw.strip().lower(), raw.strip().lower())
        if key and key not in out:
            out.append(key)
    return out or ["aspirin", "clopidogrel"]


def search(meds: list[str] | None = None) -> list[dict[str, Any]]:
    wanted = _norm_meds(meds or [])
    rows = load_json("pharmacies.json")
    scored: list[dict[str, Any]] = []
    for p in rows:
        stock = p.get("stock") or {}
        missing = [m for m in wanted if not stock.get(m)]
        has_all = len(missing) == 0
        scored.append(
            {
                **p,
                "km": km_from_phc(p["lat"], p["lng"]),
                "wanted": wanted,
                "has_all": has_all,
                "missing": missing,
                "jan_aushadhi": p.get("kind") == "jan_aushadhi",
            }
        )
    scored.sort(
        key=lambda r: (
            0 if r["jan_aushadhi"] else 1,
            0 if r["has_all"] else 1,
            r["km"],
        )
    )
    return scored


def dispatch(pharmacy_id: str, meds: list[str] | None = None) -> dict[str, Any]:
    rows = {p["id"]: p for p in search(meds)}
    if pharmacy_id not in rows:
        raise LookupError(pharmacy_id)
    pharmacy = rows[pharmacy_id]
    origin = {"lat": pharmacy["lat"], "lng": pharmacy["lng"]}
    dest = {"lat": PHC["lat"], "lng": PHC["lng"]}
    volunteer = {
        "id": "vol-pharmacy",
        "name": "Medicine courier (ASHA volunteer)",
        "kind": "courier",
        "phone": pharmacy["phone"],
    }
    trip = start_trip(origin, dest, volunteer, duration_sec=80.0, kind="courier")
    trip["pharmacy"] = pharmacy
    trip["note"] = "POC: stock is local data; WhatsApp enquiry is Phase II."
    return trip


def track_courier(trip_id: str) -> dict[str, Any]:
    return track(trip_id)
