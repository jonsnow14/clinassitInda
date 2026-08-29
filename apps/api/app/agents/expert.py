from __future__ import annotations

import uuid
from typing import Any

from ..geo import km_from_phc, load_json

_CONSULTS: dict[str, dict[str, Any]] = {}


def list_experts() -> list[dict[str, Any]]:
    rows = load_json("experts.json")
    rank = {"available": 0, "on_call": 1, "busy": 2}
    for r in rows:
        r["km"] = km_from_phc(r["lat"], r["lng"])
    rows.sort(key=lambda r: (rank.get(r["availability"], 9), r["eta_min"]))
    return rows


def connect(expert_id: str, case_summary: str = "") -> dict[str, Any]:
    experts = {e["id"]: e for e in list_experts()}
    if expert_id not in experts:
        raise LookupError(expert_id)
    expert = experts[expert_id]
    status = "connecting" if expert["availability"] != "busy" else "queued"
    if expert["availability"] == "available":
        status = "connected"
    rec = {
        "consult_id": str(uuid.uuid4()),
        "status": status,
        "expert": expert,
        "note": "Share the clinical card on this call. No video in the POC.",
        "case_summary": case_summary[:500],
    }
    _CONSULTS[rec["consult_id"]] = rec
    return rec
