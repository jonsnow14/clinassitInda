from __future__ import annotations

import time

from ..fhir import write_encounter
from ..models import (
    ClinicalCard,
    ClinicalFacts,
    Diagnosis,
    RetrievalMeta,
    Source,
    SuggestedAction,
)
from ..sarvam_client import CARD_SCHEMA, FACTS_SCHEMA, SarvamError, complete_json
from .retriever import retrieve

DISCLAIMER = (
    "ClinAssist output is decision support only. "
    "Final clinical judgment rests with the treating clinician."
)

EXTRACT_SYSTEM = """You are ClinAssistIndia, a clinical NLP extractor for Indian PHC workers.
The user message is Hinglish, Hindi, or English from a Primary Health Centre.
Extract structured clinical facts. Build english_query as a concise English retrieval string
for ICMR Standard Treatment Workflows (symptoms, duration, vitals, labs, comorbidities, likely ACS terms).
Do not diagnose. Do not invent labs that were not mentioned.
Reply with JSON only."""

GENERATE_SYSTEM = """You are ClinAssistIndia clinical decision support for a PHC medical officer in rural India.

Return JSON with ALL of these keys (never omit steps):
{
  "urgency": "urgent" | "priority" | "routine",
  "assessment": ["short Hinglish bullets"],
  "diagnosis": {"name": "condition name", "icd10": "I20.0 or null", "confidence": 0.0-1.0},
  "steps": [{"n": 1, "title": "short action", "detail": "how to do it at PHC"}],
  "do_nots": ["things not to give"],
  "referral": {"required": true, "urgency": "urgent", "destination": "where", "slip": "one line", "golden_hour_min": 90},
  "disclaimer": "ClinAssist output is decision support only. Final clinical judgment rests with the treating clinician."
}

Rules:
- Write every worker-facing string in Hindi Devanagari (not roman Hinglish). Keep drug names, ECG, ICD codes in Latin if needed.
- PHC-feasible steps only, copied from the ICMR passages (ECG, antiplatelets, oxygen, refer).
- steps MUST be a non-empty array of objects with n, title, detail. At least 3 steps if passages mention any treatment.
- Do not invent doses that are not in the passages.
- Chest pain + diabetes + sweating with NSTEMI/UA passages => urgency urgent, diagnosis Unstable angina/NSTEMI if the passages say so.
- Always include the disclaimer string exactly as above.
Reply with JSON only."""


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_str(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(x).strip() for x in value if str(x).strip()]
        return ", ".join(parts) or None
    if isinstance(value, dict):
        return ", ".join(f"{k} {v}" for k, v in value.items()) or None
    text = str(value).strip()
    return text or None


def coerce_facts(raw: dict) -> dict:
    out = dict(raw)
    out["symptoms"] = [str(s) for s in _as_list(out.get("symptoms"))]
    out["comorbidities"] = [str(s) for s in _as_list(out.get("comorbidities"))]
    out["duration"] = _as_str(out.get("duration"))
    out["sex"] = _as_str(out.get("sex"))
    age = out.get("age")
    if isinstance(age, list) and age:
        age = age[0]
    try:
        out["age"] = int(age) if age not in (None, "") else None
    except (TypeError, ValueError):
        out["age"] = None
    vitals = out.get("vitals") or {}
    labs = out.get("labs") or {}
    if not isinstance(vitals, dict):
        vitals = {"note": str(vitals)}
    if not isinstance(labs, dict):
        labs = {"note": str(labs)}
    out["vitals"] = {str(k): str(v) for k, v in vitals.items()}
    out["labs"] = {str(k): str(v) for k, v in labs.items()}
    query = _as_str(out.get("english_query"))
    if not query:
        bits = out["symptoms"] + list(out["vitals"].values()) + list(out["labs"].values())
        query = " ".join(bits) or "primary care clinical query"
    out["english_query"] = query
    return out


def _confidence(value) -> float:
    if value is None:
        return 0.5
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    s = str(value).strip().lower()
    return {"high": 0.85, "medium": 0.55, "moderate": 0.55, "low": 0.35, "uncertain": 0.25}.get(s, 0.5)


def _parse_dx_string(text: str) -> tuple[str, str | None]:
    import re

    icd = None
    m = re.search(r"\b([A-TV-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?)\b", text, re.I)
    if m:
        icd = m.group(1).upper()
    name = text
    par = re.search(r"\(([^)]+)\)", text)
    if par:
        name = par.group(1).strip()
    elif ":" in text:
        name = text.split(":", 1)[-1].strip()
    name = re.sub(r"^\s*ICD-?1[01]\s*", "", name, flags=re.I).strip(" :-")
    return name or text, icd


def _harvest_steps(raw: dict) -> list:
    for key in (
        "steps",
        "action_steps",
        "actions",
        "immediate_actions",
        "phc_steps",
        "management",
        "plan",
        "recommendations",
        "abhi_kya_karein",
        "what_to_do",
    ):
        val = raw.get(key)
        if val:
            return _as_list(val)
    return []


def coerce_card(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    # unwrap a single nested object
    for wrap in ("card", "clinical_card", "response", "result", "data"):
        inner = raw.get(wrap)
        if isinstance(inner, dict) and ("steps" in inner or "diagnosis" in inner or "urgency" in inner):
            raw = {**raw, **inner}
            break
    out = dict(raw)
    urg = str(out.get("urgency") or "priority").lower()
    out["urgency"] = urg if urg in {"urgent", "priority", "routine"} else "priority"
    assess = out.get("assessment") or out.get("summary") or out.get("picture") or out.get("findings")
    out["assessment"] = [str(a) for a in _as_list(assess) if str(a).strip()]
    dx = out.get("diagnosis")
    if isinstance(dx, str):
        name, icd = _parse_dx_string(dx)
        out["diagnosis"] = {"name": name, "icd10": icd or out.get("icd10"), "confidence": _confidence(out.get("confidence"))}
    elif isinstance(dx, dict):
        name = str(dx.get("name") or dx.get("label") or "Unspecified")
        icd = dx.get("icd10") or dx.get("icd") or dx.get("code")
        if isinstance(name, str) and not icd:
            parsed_name, parsed_icd = _parse_dx_string(name)
            name, icd = parsed_name, parsed_icd
        out["diagnosis"] = {
            "name": name,
            "icd10": icd,
            "confidence": _confidence(dx.get("confidence") or out.get("confidence")),
        }
    else:
        out["diagnosis"] = {"name": "Unspecified", "icd10": None, "confidence": 0.2}
    steps = []
    for i, step in enumerate(_harvest_steps(out), start=1):
        if isinstance(step, str):
            steps.append({"n": i, "title": step.split(".")[0][:80], "detail": step})
        elif isinstance(step, dict):
            steps.append(
                {
                    "n": int(step.get("n") or i),
                    "title": str(step.get("title") or step.get("action") or f"Step {i}"),
                    "detail": str(step.get("detail") or step.get("text") or step.get("title") or ""),
                }
            )
    out["steps"] = steps
    out["do_nots"] = [str(x) for x in _as_list(out.get("do_nots") or out.get("do_not"))]
    ref = out.get("referral")
    if isinstance(ref, str):
        out["referral"] = {
            "required": True,
            "urgency": out["urgency"],
            "destination": ref,
            "slip": ref,
            "golden_hour_min": out.get("golden_hour_min"),
        }
    elif isinstance(ref, dict):
        ru = str(ref.get("urgency") or out["urgency"]).lower()
        out["referral"] = {
            "required": bool(ref.get("required", True)),
            "urgency": ru if ru in {"urgent", "priority", "routine"} else out["urgency"],
            "destination": str(ref.get("destination") or ref.get("to") or ""),
            "slip": str(ref.get("slip") or ref.get("note") or ""),
            "golden_hour_min": ref.get("golden_hour_min"),
        }
    else:
        out["referral"] = {
            "required": False,
            "urgency": "routine",
            "destination": "",
            "slip": "",
            "golden_hour_min": None,
        }
    if not out["assessment"]:
        out["assessment"] = [out["diagnosis"]["name"]]
    return out


def _steps_from_chunks(chunks) -> list[dict]:
    import re

    keys = (
        "ecg",
        "aspirin",
        "clopidogrel",
        "prasugrel",
        "ticagrelor",
        "troponin",
        "heparin",
        "enoxaparin",
        "refer",
        "phc",
        "oxygen",
        "metoprolol",
        "statin",
        "nitrate",
    )
    steps: list[dict] = []
    seen: set[str] = set()
    for ch in chunks:
        pieces = re.split(r"[\n;]|[0-9]+\.\s+", ch.text)
        for piece in pieces:
            s = " ".join(piece.split()).strip(" -•")
            if len(s) < 12 or len(s) > 240:
                continue
            low = s.lower()
            if not any(k in low for k in keys):
                continue
            sig = low[:70]
            if sig in seen:
                continue
            seen.add(sig)
            steps.append({"n": len(steps) + 1, "title": s[:90], "detail": s})
            if len(steps) >= 8:
                return steps
    return steps


def _dx_from_sources(sources: list[Source], facts: ClinicalFacts) -> Diagnosis | None:
    blob = " ".join(s.stw_title + " " + s.quote for s in sources).lower()
    comorbid = " ".join(facts.comorbidities + facts.symptoms).lower()
    if "nstemi" in blob or "unstable angina" in blob:
        return Diagnosis(name="Unstable angina / NSTEMI", icd10="I20.0", confidence=0.72)
    if "stemi" in blob and "nstemi" not in blob:
        return Diagnosis(name="STEMI suspected", icd10="I21.0", confidence=0.7)
    if "chest" in comorbid or "chest" in blob:
        return Diagnosis(name="Acute chest pain — rule out ACS", icd10=None, confidence=0.55)
    return None


def _assessment_from_facts(facts: ClinicalFacts, note: str) -> list[str]:
    items: list[str] = []
    if facts.age:
        items.append(f"{facts.age} saal" + (f" {facts.sex}" if facts.sex else ""))
    items.extend(facts.symptoms)
    items.extend(f"{k}: {v}" for k, v in facts.vitals.items())
    items.extend(f"{k}: {v}" for k, v in facts.labs.items())
    items.extend(facts.comorbidities)
    if facts.duration:
        items.append(f"Duration: {facts.duration}")
    if not items:
        items.append(note[:180])
    # unique preserve order
    out: list[str] = []
    seen: set[str] = set()
    for it in items:
        key = it.strip().lower()
        if not key or key in seen or key == "unspecified":
            continue
        seen.add(key)
        out.append(it.strip())
    return out


def _enrich(card: ClinicalCard, facts: ClinicalFacts, chunks, sources: list[Source], note: str) -> ClinicalCard:
    if not card.steps:
        extracted = _steps_from_chunks(chunks)
        if extracted:
            from ..models import ActionStep

            card.steps = [ActionStep.model_validate(s) for s in extracted]
    if card.diagnosis.name.lower() in {"unspecified", "unknown", ""}:
        guessed = _dx_from_sources(sources, facts)
        if guessed:
            card.diagnosis = guessed
    weak_assess = [a for a in card.assessment if a.strip().lower() not in {"unspecified", "unknown", ""}]
    if not weak_assess:
        card.assessment = _assessment_from_facts(facts, note)
    else:
        card.assessment = weak_assess
    cardiac = "nstemi" in (card.diagnosis.name + " ".join(s.stw_title for s in sources)).lower()
    if cardiac and not card.referral.required:
        card.referral.required = True
        card.referral.urgency = "urgent"
        card.referral.destination = card.referral.destination or "District Hospital / PCI-capable centre"
        card.referral.slip = card.referral.slip or (
            f"{facts.age or '?'}{facts.sex or ''}, {card.diagnosis.name}. "
            "PHC se refer. ECG/troponin ke saath bhejein."
        )
        card.referral.golden_hour_min = card.referral.golden_hour_min or 90
        card.urgency = "urgent"
    if cardiac and not card.do_nots:
        card.do_nots = [
            "NSAIDs (diclofenac/ibuprofen) mat do",
            "Routine oxygen mat do agar SpO2 >= 94%",
        ]
    return card


def _suggested(card: ClinicalCard) -> list[SuggestedAction]:
    actions: list[SuggestedAction] = ["sos"]
    blob = " ".join(
        [card.diagnosis.name]
        + card.assessment
        + [s.title + " " + s.detail for s in card.steps]
        + card.do_nots
        + [card.referral.slip, card.referral.destination]
    ).lower()
    if card.referral.required or card.urgency == "urgent":
        actions.extend(["beds", "transport", "expert"])
    if any(tok in blob for tok in ("aspirin", "clopidogrel", "statin", "heparin", "metformin", "tablet", "mg")):
        actions.append("pharmacy")
    # unique, stable order
    order: list[SuggestedAction] = ["beds", "transport", "pharmacy", "expert", "sos"]
    return [a for a in order if a in set(actions)]


def consult(text: str, phc_id: str = "phc-purnia") -> ClinicalCard:
    t0 = time.time()
    stripped = text.strip()
    if not stripped:
        raise ValueError("empty consult text")

    facts_raw, model = complete_json(
        system=EXTRACT_SYSTEM,
        user=stripped,
        schema_name="clinical_facts",
        schema=FACTS_SCHEMA,
        max_tokens=800,
    )
    try:
        facts = ClinicalFacts.model_validate(coerce_facts(facts_raw))
    except Exception as exc:  # noqa: BLE001
        raise SarvamError(f"could not parse Sarvam clinical facts: {exc}") from exc
    blob = f"{stripped} {facts.english_query} {' '.join(facts.labs)} {' '.join(facts.symptoms)}".lower()
    queries = [facts.english_query.strip() or stripped]
    compact = " ".join(
        facts.symptoms
        + [f"{k} {v}" for k, v in facts.vitals.items()]
        + [f"{k} {v}" for k, v in facts.labs.items()]
    )
    if compact:
        queries.append(compact)
    cardiac_hints = ("troponin", "sob", "chest", "nstemi", "stemi", "acs", "angina", "saans", "mi ")
    if any(h in blob for h in cardiac_hints):
        queries.append("unstable angina NSTEMI ACS troponin PHC aspirin clopidogrel ECG")
    seen: set[tuple] = set()
    chunks = []
    for q in queries:
        if not q:
            continue
        for ch in retrieve(q, k=4):
            key = (ch.pdf, ch.section, ch.text[:80])
            if key in seen:
                continue
            seen.add(key)
            chunks.append(ch)
    chunks.sort(key=lambda c: c.score or 0, reverse=True)
    chunks = chunks[:6]
    if not chunks:
        chunks = retrieve((facts.english_query or stripped) + " primary care PHC referral", k=6)

    context_blocks = []
    sources: list[Source] = []
    for i, ch in enumerate(chunks, start=1):
        context_blocks.append(f"[{i}] {ch.stw_title} ({ch.pdf} {ch.section})\n{ch.text}")
        quote = ch.text.replace("\n", " ")
        sources.append(
            Source(
                n=i,
                stw_title=ch.stw_title,
                section=ch.section,
                quote=quote[:400],
                pdf=ch.pdf,
            )
        )

    if not chunks:
        raise SarvamError("No ICMR passages retrieved. Re-run ingest.")

    user = (
        f"Worker note:\n{stripped}\n\n"
        f"Structured facts:\n{facts.model_dump_json()}\n\n"
        f"ICMR passages:\n" + "\n\n".join(context_blocks)
    )
    card_raw, model = complete_json(
        system=GENERATE_SYSTEM,
        user=user,
        schema_name="clinical_card",
        schema=CARD_SCHEMA,
        max_tokens=2048,
    )
    card_raw.pop("sources", None)
    card_raw.pop("suggested_actions", None)
    card_raw.pop("retrieval", None)
    card_raw.pop("fhir_id", None)
    card_raw["disclaimer"] = DISCLAIMER
    try:
        card_raw = coerce_card(card_raw)
        card = ClinicalCard.model_validate(
            {
                **card_raw,
                "sources": [s.model_dump() for s in sources],
                "suggested_actions": [],
                "retrieval": RetrievalMeta(
                    chunk_count=len(chunks),
                    top_score=chunks[0].score if chunks else None,
                ).model_dump(),
                "latency_ms": 0,
                "model": model,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise SarvamError(f"could not parse Sarvam clinical card: {exc}") from exc
    if not card.disclaimer:
        card.disclaimer = DISCLAIMER
    card = _enrich(card, facts, chunks, sources, stripped)
    card.suggested_actions = _suggested(card)
    if card.diagnosis.confidence < 0.4 and "expert" not in card.suggested_actions:
        card.suggested_actions = ["expert", *card.suggested_actions]
    if not chunks or (chunks[0].score is not None and chunks[0].score < 0.42):
        if "expert" not in card.suggested_actions:
            card.suggested_actions.insert(0, "expert")

    display = f"{facts.age or '?'}{facts.sex or ''}".strip() or "PHC patient"
    try:
        card.fhir_id = write_encounter(card, display, phc_id)
    except Exception:
        card.fhir_id = None

    card.latency_ms = int((time.time() - t0) * 1000)
    card.model = model
    try:
        from ..mayura import hindi_card

        card = hindi_card(card)
    except Exception:
        import logging

        logging.getLogger("clinassist").exception("Mayura card translation failed")
    card.latency_ms = int((time.time() - t0) * 1000)
    return card
