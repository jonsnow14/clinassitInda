from __future__ import annotations

import json
import os
import re
from typing import Any

PRIMARY_MODEL = os.getenv("SARVAM_MODEL", "sarvam-105b")
FALLBACK_MODEL = "sarvam-105b-conversations"
SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"

FACTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "age": {"type": ["integer", "null"]},
        "sex": {"type": ["string", "null"]},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "duration": {"type": ["string", "null"]},
        "vitals": {"type": "object", "additionalProperties": {"type": "string"}},
        "labs": {"type": "object", "additionalProperties": {"type": "string"}},
        "comorbidities": {"type": "array", "items": {"type": "string"}},
        "english_query": {"type": "string"},
    },
    "required": ["english_query", "symptoms", "vitals", "labs", "comorbidities"],
}

CARD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "urgency": {"type": "string", "enum": ["urgent", "priority", "routine"]},
        "assessment": {"type": "array", "items": {"type": "string"}},
        "diagnosis": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "icd10": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
            },
            "required": ["name", "confidence"],
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "n": {"type": "integer"},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["n", "title", "detail"],
            },
        },
        "do_nots": {"type": "array", "items": {"type": "string"}},
        "referral": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "required": {"type": "boolean"},
                "urgency": {"type": "string", "enum": ["urgent", "priority", "routine"]},
                "destination": {"type": "string"},
                "slip": {"type": "string"},
                "golden_hour_min": {"type": ["integer", "null"]},
            },
            "required": ["required", "urgency", "destination", "slip"],
        },
        "disclaimer": {"type": "string"},
    },
    "required": ["urgency", "assessment", "diagnosis", "steps", "do_nots", "referral", "disclaimer"],
}


class SarvamError(RuntimeError):
    """Exception raised for Sarvam API service errors or failure conditions."""

    pass


def key_present() -> bool:
    """Check whether the Sarvam API key environment variable is set.

    Returns:
        True if `SARVAM_API_KEY` is present in the environment, False otherwise.
    """
    return bool(os.getenv("SARVAM_API_KEY"))


def _key() -> str:
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        raise SarvamError("SARVAM_API_KEY is not set")
    return key


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _post(payload: dict[str, Any]) -> dict[str, Any]:
    import httpx

    key = _key()
    headers = {
        "api-subscription-key": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(SARVAM_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise SarvamError(f"Sarvam HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()


def complete_json(
    *,
    system: str,
    user: str,
    schema_name: str,
    schema: dict[str, Any],
    max_tokens: int = 2048,
) -> tuple[dict[str, Any], str]:
    """Execute a structured completion call returning parsed JSON and model ID.

    Sends completion requests to Sarvam chat API with system prompt instructions to produce
    a single JSON object response. Uses primary model with automated fallback.

    Args:
        system: System prompt instructions outlining behavior and guidelines.
        user: User query or prompt payload.
        schema_name: Identifier name for the schema parameter (unused by model).
        schema: Dictionary schema definition used for validation context.
        max_tokens: Maximum completion output tokens allowed. Defaults to 2048.

    Returns:
        A tuple containing the parsed dictionary JSON object and model identifier string used.

    Raises:
        SarvamError: If API execution fails across all model candidates or parsing fails.
    """
    del schema_name, schema  # schema is enforced in the prompt + Pydantic, not by Sarvam json_schema
    sys_json = system + "\nReply with a single JSON object only. No markdown fences."
    messages = [
        {"role": "system", "content": sys_json},
        {"role": "user", "content": user},
    ]
    models = [PRIMARY_MODEL]
    if FALLBACK_MODEL not in models:
        models.append(FALLBACK_MODEL)
    last_err: Exception | None = None
    for model in models:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "wiki_grounding": False,
            "response_format": {"type": "json_object"},
        }
        try:
            data = _post(payload)
            msg = ((data.get("choices") or [{}])[0].get("message") or {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return _extract_json(content), data.get("model") or model
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    raise SarvamError(f"Sarvam JSON completion failed: {last_err}") from last_err
