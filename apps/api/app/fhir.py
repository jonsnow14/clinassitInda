from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .models import ClinicalCard
from .paths import FHIR_DIR


def write_encounter(card: ClinicalCard, patient_display: str, phc_id: str) -> str:
    """Generate and write a FHIR Bundle containing clinical encounter resources.

    Creates an Encounter resource, associated MedicationRequest resources for key
    cardiac medications, and a ServiceRequest for referrals based on the provided
    ClinicalCard. The bundle is serialized as JSON and stored in the configured FHIR directory.

    Args:
        card: ClinicalCard instance containing assessment, steps, and referral information.
        patient_display: Display name or identifier for the subject patient.
        phc_id: Identifier of the primary health centre requesting or managing care.

    Returns:
        The generated unique UUID string representing the encounter ID.
    """
    FHIR_DIR.mkdir(parents=True, exist_ok=True)
    encounter_id = str(uuid.uuid4())
    meds = [
        {
            "resourceType": "MedicationRequest",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {"text": step.title},
            "dosageInstruction": [{"text": step.detail}],
        }
        for step in card.steps
        if any(token in (step.title + step.detail).lower() for token in ("aspirin", "clopidogrel", "heparin", "statin"))
    ]
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": encounter_id,
                    "status": "in-progress",
                    "class": {"code": "AMB", "display": "ambulatory"},
                    "subject": {"display": patient_display},
                    "serviceProvider": {"display": phc_id},
                    "reasonCode": [{"text": card.diagnosis.name}],
                    "diagnosis": [
                        {
                            "condition": {
                                "display": card.diagnosis.name,
                                "coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": card.diagnosis.icd10}]
                                if card.diagnosis.icd10
                                else [],
                            },
                            "use": {"coding": [{"code": "working"}]},
                        }
                    ],
                }
            },
            *[{"resource": m} for m in meds],
            {
                "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "active" if card.referral.required else "draft",
                    "intent": "order",
                    "priority": "stat" if card.urgency == "urgent" else "routine",
                    "code": {"text": "Referral"},
                    "requester": {"display": phc_id},
                    "performer": [{"display": card.referral.destination}],
                    "note": [{"text": card.referral.slip}],
                }
            },
        ],
    }
    path = FHIR_DIR / f"{encounter_id}.json"
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return encounter_id
