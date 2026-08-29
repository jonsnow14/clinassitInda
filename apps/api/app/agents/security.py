from __future__ import annotations

import time
import uuid
from typing import Any

from ..geo import load_json

_SOS: dict[str, dict[str, Any]] = {}


def raise_sos(reason: str, note: str = "") -> dict[str, Any]:
    contacts = load_json("sos_contacts.json")
    if reason == "security":
        targets = [c for c in contacts if c["kind"] in {"police", "admin"}]
    else:
        targets = [c for c in contacts if c["kind"] in {"community", "volunteer", "police"}]
    sos_id = str(uuid.uuid4())
    rec = {
        "id": sos_id,
        "reason": reason,
        "note": note,
        "created_ts": time.time(),
        "contacts_notified": targets,
        "ack": "pending",
        "eta_min": 8 if reason == "security" else 12,
    }
    _SOS[sos_id] = rec
    return status(sos_id)


def status(sos_id: str) -> dict[str, Any]:
    rec = _SOS.get(sos_id)
    if not rec:
        raise KeyError(sos_id)
    elapsed = time.time() - rec["created_ts"]
    if elapsed > 6:
        rec["ack"] = "acked"
        rec["eta_min"] = max(1, rec["eta_min"] - int(elapsed / 8))
    return rec
