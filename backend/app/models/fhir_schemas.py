from pydantic import BaseModel
from typing import List, Optional

class Coding(BaseModel):
    system: str
    code: str
    display: str

class CodeableConcept(BaseModel):
    coding: List[Coding]

class FHIRPatient(BaseModel):
    resourceType: str = "Patient"
    id: str
    gender: str
    age: int

class FHIREncounter(BaseModel):
    resourceType: str = "Encounter"
    status: str
    subject: dict  # Reference to Patient
    diagnosis: List[dict]
    hospitalization: Optional[dict] = None

class FHIRMedicationRequest(BaseModel):
    resourceType: str = "MedicationRequest"
    status: str
    intent: str
    subject: dict
    medicationCodeableConcept: CodeableConcept
    dosageInstruction: List[dict]

class FHIRServiceRequest(BaseModel):
    resourceType: str = "ServiceRequest"
    status: str
    intent: str
    category: List[CodeableConcept]
    priority: str
    subject: dict

