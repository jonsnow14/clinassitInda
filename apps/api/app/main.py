from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import geo
from .agents import expert as expert_agent
from .agents import ops
from .agents import pharmacy as pharmacy_agent
from .agents import security as sos_agent
from .models import (
    ClinicalConsultRequest,
    ExpertConsultRequest,
    HindiScriptRequest,
    PharmacyDispatchRequest,
    SosRequest,
    TransportDispatchRequest,
)
from .paths import load_dotenv
from .rag.ingest import chroma_ready
from .sarvam_client import SarvamError, key_present


def _hi(payload: Any) -> Any:
    """Translate payload prose to Hindi if Sarvam API key is configured.

    Args:
        payload: Any serializable object or dictionary.

    Returns:
        Translated payload object or original payload if translation is unavailable/fails.
    """
    if not key_present():
        return payload
    try:
        from .mayura import hindi_payload

        return hindi_payload(payload)
    except Exception:
        return payload

load_dotenv()

app = FastAPI(title="ClinAssistIndia", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/health")
def health() -> dict[str, Any]:
    """Retrieve service health status, vector index state, and configuration details.

    Returns:
        Dictionary containing service readiness indicators, active model name, and base PHC info.
    """
    model = os.getenv("SARVAM_MODEL", "sarvam-105b")
    return {
        "ok": True,
        "chroma_ready": chroma_ready(),
        "sarvam_key_present": key_present(),
        "model": model,
        "phc": geo.PHC,
    }


@app.post("/v1/script/hindi")
def script_hindi(body: HindiScriptRequest) -> dict[str, str]:
    """Convert input English or transliterated script to Hindi Devanagari script.

    Args:
        body: Request containing input text string.

    Returns:
        Dictionary with translated text and model identifier.

    Raises:
        HTTPException: 503 if API key missing or translation service call fails.
    """
    if not key_present():
        raise HTTPException(503, "SARVAM_API_KEY is not set")
    try:
        from .mayura import mayura_hindi

        hindi = mayura_hindi(body.text)
        return {"text": hindi, "model": "mayura:v1"}
    except SarvamError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/v1/clinical/consult")
def clinical_consult(body: ClinicalConsultRequest) -> dict[str, Any]:
    """Process a clinical consultation query and generate clinical decision card.

    Extracts clinical facts, retrieves relevant ICMR guidelines, and generates structured
    card outputs with diagnoses, action steps, referral info, and references.

    Args:
        body: Consultation request containing query text and PHC identifier.

    Returns:
        Structured clinical decision card dictionary.

    Raises:
        HTTPException: 400 for empty queries or bad input; 503 if services unavailable; 500 on execution error.
    """
    if not body.text.strip():
        raise HTTPException(400, "empty consult text")
    if not key_present():
        raise HTTPException(503, "SARVAM_API_KEY is not set")
    if not chroma_ready():
        raise HTTPException(503, "ICMR index not ready. Run python -m app.rag.ingest")
    try:
        from .rag.clinical_agent import consult

        return consult(body.text, body.phc_id)
    except SarvamError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        import logging
        import traceback

        logging.getLogger("clinassist").exception("clinical consult failed")
        raise HTTPException(500, f"clinical consult failed: {exc}\n{traceback.format_exc()[-800:]}") from exc


@app.get("/v1/beds")
def beds(need: Literal["icu", "oxygen", "general"] = Query("icu")) -> dict[str, Any]:
    """List facility hospital bed availability filtered by bed type.

    Args:
        need: Specific bed type requirement ("icu", "oxygen", or "general"). Defaults to "icu".

    Returns:
        Dictionary containing facility details and estimated bed availabilities.
    """
    return _hi(
        {
            "phc": geo.PHC,
            "need": need,
            "note": "POC directory of real Purnia facilities. Bed counts are local estimates, not live HMIS/ABDM.",
            "hospitals": ops.list_beds(need),
        }
    )


@app.get("/v1/transport")
def transport(kind: Literal["ambulance", "volunteer"] | None = None) -> dict[str, Any]:
    """List available emergency transport vehicles filtered by kind.

    Args:
        kind: Optional transport vehicle filter ("ambulance" or "volunteer").

    Returns:
        Dictionary listing matching transport vehicles.
    """
    return _hi({"phc": geo.PHC, "vehicles": ops.list_transport(kind)})


@app.post("/v1/transport/dispatch")
def transport_dispatch(body: TransportDispatchRequest) -> dict[str, Any]:
    """Dispatch emergency transport based on requirements.

    Args:
        body: Request specifying transport kind and oxygen requirement.

    Returns:
        Dictionary containing dispatch confirmation and initial trip status.

    Raises:
        HTTPException: 404 if no suitable transport vehicle is available.
    """
    try:
        return _hi(ops.dispatch_transport(body.kind, body.need_oxygen))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/v1/transport/{trip_id}/track")
def transport_track(trip_id: str) -> dict[str, Any]:
    """Track current real-time position and ETA of an active transport trip.

    Args:
        trip_id: Unique identifier string for transport trip.

    Returns:
        Dictionary containing tracking coordinates, progress, and ETA.

    Raises:
        HTTPException: 404 if trip_id is unknown.
    """
    try:
        return ops.track_transport(trip_id)
    except KeyError:
        raise HTTPException(404, "unknown trip") from None


@app.get("/v1/pharmacy")
def pharmacy(meds: str = Query("aspirin,clopidogrel")) -> dict[str, Any]:
    """Search regional pharmacies for specified medication availability.

    Args:
        meds: Comma-separated list of medication names. Defaults to "aspirin,clopidogrel".

    Returns:
        Dictionary containing matching pharmacies and stock availability.
    """
    wanted = [m.strip() for m in meds.split(",") if m.strip()]
    return _hi(
        {
            "note": "POC: stock is local data; WhatsApp enquiry is Phase II. Jan Aushadhi listed first.",
            "meds": wanted,
            "pharmacies": pharmacy_agent.search(wanted),
        }
    )


@app.post("/v1/pharmacy/dispatch")
def pharmacy_dispatch(body: PharmacyDispatchRequest) -> dict[str, Any]:
    """Dispatch courier delivery for requested medications from a pharmacy.

    Args:
        body: Request containing pharmacy ID and list of required medications.

    Returns:
        Dictionary confirming courier dispatch and initial tracking status.

    Raises:
        HTTPException: 404 if targeted pharmacy is not found.
    """
    try:
        return _hi(pharmacy_agent.dispatch(body.pharmacy_id, body.meds))
    except LookupError:
        raise HTTPException(404, "unknown pharmacy") from None


@app.get("/v1/courier/{trip_id}/track")
def courier_track(trip_id: str) -> dict[str, Any]:
    """Track location and ETA of an active pharmacy courier delivery trip.

    Args:
        trip_id: Unique identifier for the courier trip.

    Returns:
        Dictionary containing tracking progress and updated status.

    Raises:
        HTTPException: 404 if courier trip is unknown.
    """
    try:
        return pharmacy_agent.track_courier(trip_id)
    except KeyError:
        raise HTTPException(404, "unknown trip") from None


@app.post("/v1/sos")
def sos_raise(body: SosRequest) -> dict[str, Any]:
    """Trigger an emergency SOS alert signal.

    Args:
        body: Request specifying SOS reason and descriptive note.

    Returns:
        Dictionary confirming created SOS alert status.
    """
    return _hi(sos_agent.raise_sos(body.reason, body.note))


@app.get("/v1/sos/{sos_id}")
def sos_status(sos_id: str) -> dict[str, Any]:
    """Retrieve current status of a previously raised SOS alert.

    Args:
        sos_id: Unique identifier string for the SOS signal.

    Returns:
        Dictionary containing current SOS response status.

    Raises:
        HTTPException: 404 if SOS ID is not found.
    """
    try:
        return sos_agent.status(sos_id)
    except KeyError:
        raise HTTPException(404, "unknown sos") from None


@app.get("/v1/experts")
def experts() -> dict[str, Any]:
    """List available specialist physicians and expert advisors for consultation.

    Returns:
        Dictionary containing list of available experts.
    """
    return _hi({"experts": expert_agent.list_experts()})


@app.post("/v1/experts/{expert_id}/consult")
def expert_consult(expert_id: str, body: ExpertConsultRequest) -> dict[str, Any]:
    """Request a tele-consultation connection with a named specialist.

    Args:
        expert_id: Unique identifier string for the expert.
        body: Request containing clinical case summary.

    Returns:
        Dictionary with consultation details and connection status.

    Raises:
        HTTPException: 404 if expert_id is unknown.
    """
    try:
        return _hi(expert_agent.connect(expert_id, body.case_summary))
    except LookupError:
        raise HTTPException(404, "unknown expert") from None
