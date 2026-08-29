from __future__ import annotations

import re
from typing import Any

from .sarvam_client import SarvamError, _key

MAYURA_URL = "https://api.sarvam.ai/translate"
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
SEP = "\n§§\n"
SKIP_KEYS = {
    "id",
    "phone",
    "lat",
    "lng",
    "trip_id",
    "pdf",
    "kind",
    "type",
    "polyline",
    "stock",
    "wanted",
    "missing",
    "icd10",
    "fhir_id",
    "model",
    "pincode",
    "consult_id",
    "page",
    "urgency",
    "suggested_actions",
    "status",
    "availability",
    "need",
    "n",
    "confidence",
    "latency_ms",
    "chunk_count",
    "top_score",
    "accepts_nstemi",
    "jan_aushadhi",
    "has_all",
    "oxygen",
    "available",
    "eta_min",
    "progress",
    "ack",
    "reason",
    "km",
    "beds_icu",
    "beds_oxygen",
    "beds_general",
}


def deva_ratio(text: str) -> float:
    """Calculate the proportion of Devanagari characters among letters in a text string.

    Args:
        text: Input string to analyze.

    Returns:
        Float ratio between 0.0 and 1.0 representing Devanagari character frequency.
    """
    if not text:
        return 1.0
    letters = [ch for ch in text if ch.isalpha() or "\u0900" <= ch <= "\u097f"]
    if not letters:
        return 1.0
    return sum(1 for ch in letters if "\u0900" <= ch <= "\u097f") / len(letters)


LATIN_WORD = re.compile(r"[A-Za-z]{2,}")


def needs_hindi(text: str) -> bool:
    """Determine if input text requires translation to Hindi.

    Args:
        text: Input text string to evaluate.

    Returns:
        True if text contains Latin words or low Devanagari ratio, False otherwise.
    """
    t = (text or "").strip()
    if len(t) < 2:
        return False
    # Mixed Devanagari + leftover roman (second sentence typed after first converted)
    if LATIN_WORD.search(t):
        return True
    return deva_ratio(t) < 0.4


def mayura_hindi(text: str) -> str:
    """Translate input text to Hindi using the Sarvam Mayura translation API model.

    Args:
        text: Source text string in English or code-mixed Hindi/English.

    Returns:
        Translated Hindi text string in Devanagari script.

    Raises:
        SarvamError: If Mayura translation API request fails with error HTTP status.
    """
    t = (text or "").strip()
    if not t or not needs_hindi(t):
        return text
    import httpx

    key = _key()
    payload = {
        "input": t[:1000],
        "source_language_code": "auto",
        "target_language_code": "hi-IN",
        "model": "mayura:v1",
        "mode": "code-mixed",
        "output_script": "fully-native",
        "numerals_format": "international",
    }
    headers = {
        "api-subscription-key": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(MAYURA_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            payload.pop("output_script", None)
            resp = client.post(MAYURA_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise SarvamError(f"Mayura HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    return (data.get("translated_text") or text).strip() or text


def mayura_many(parts: list[str]) -> list[str]:
    """Translate multiple string fragments into Hindi in batched Mayura requests.

    Args:
        parts: List of text strings needing translation.

    Returns:
        List of translated strings corresponding to input parts.
    """
    out = list(parts)
    pending: list[int] = [i for i, p in enumerate(parts) if needs_hindi(p)]
    i = 0
    while i < len(pending):
        chunk_idx: list[int] = []
        buf: list[str] = []
        while i < len(pending):
            piece = parts[pending[i]].replace("§§", " ")
            trial = SEP.join(buf + [piece])
            if buf and len(trial) > 900:
                break
            buf.append(piece)
            chunk_idx.append(pending[i])
            i += 1
        if not buf:
            i += 1
            continue
        translated = mayura_hindi(SEP.join(buf))
        bits = [b.strip() for b in translated.split("§§")]
        if len(bits) != len(buf):
            for j, idx in enumerate(chunk_idx):
                out[idx] = mayura_hindi(parts[idx])
        else:
            for idx, bit in zip(chunk_idx, bits):
                out[idx] = bit or parts[idx]
    return out


def _collect(obj: Any, acc: list[str]) -> None:
    if isinstance(obj, str):
        if needs_hindi(obj):
            acc.append(obj)
        return
    if isinstance(obj, list):
        for x in obj:
            _collect(x, acc)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS or k.endswith("_id"):
                continue
            _collect(v, acc)


def _apply(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, str):
        return mapping.get(obj, obj)
    if isinstance(obj, list):
        return [_apply(x, mapping) for x in obj]
    if isinstance(obj, dict):
        return {
            k: v if k in SKIP_KEYS or k.endswith("_id") else _apply(v, mapping)
            for k, v in obj.items()
        }
    return obj


def hindi_card(card: Any) -> Any:
    """Translate worker-facing prose of a ClinicalCard object to Hindi.

    Translates assessment points, diagnosis name, step titles and details, do-nots,
    referral fields, disclaimer, and sources into Hindi while preserving enums and metadata.

    Args:
        card: ClinicalCard object instance.

    Returns:
        The mutated ClinicalCard instance with translated prose fields.
    """
    bag: list[str] = []

    def take(s: str | None) -> int:
        bag.append(s or "")
        return len(bag) - 1

    a_ids = [take(x) for x in card.assessment]
    dx_id = take(card.diagnosis.name)
    step_ids = [(take(s.title), take(s.detail)) for s in card.steps]
    dn_ids = [take(x) for x in card.do_nots]
    dest_id = take(card.referral.destination)
    slip_id = take(card.referral.slip)
    disc_id = take(card.disclaimer)
    src_ids = [(take(s.stw_title), take(s.quote)) for s in card.sources]
    out = mayura_many(bag)
    card.assessment = [out[i] or card.assessment[n] for n, i in enumerate(a_ids)]
    card.diagnosis.name = out[dx_id] or card.diagnosis.name
    for s, (ti, di) in zip(card.steps, step_ids):
        s.title = out[ti] or s.title
        s.detail = out[di] or s.detail
    card.do_nots = [out[i] or card.do_nots[n] for n, i in enumerate(dn_ids)]
    card.referral.destination = out[dest_id] or card.referral.destination
    card.referral.slip = out[slip_id] or card.referral.slip
    card.disclaimer = out[disc_id] or card.disclaimer
    for s, (ti, qi) in zip(card.sources, src_ids):
        s.stw_title = out[ti] or s.stw_title
        s.quote = out[qi] or s.quote
    return card


def hindi_payload(obj: Any) -> Any:
    """Recursively translate string fields within arbitrary dictionary/list data structures to Hindi.

    Args:
        obj: Dictionary, list, string, or scalar data structure.

    Returns:
        New data structure with translated string values, ignoring system/metadata keys.
    """
    acc: list[str] = []
    _collect(obj, acc)
    uniq = list(dict.fromkeys(acc))
    if not uniq:
        return obj
    mapped = dict(zip(uniq, mayura_many(uniq)))
    return _apply(obj, mapped)
