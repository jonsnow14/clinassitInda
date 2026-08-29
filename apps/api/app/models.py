from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Urgency = Literal["urgent", "priority", "routine"]
SuggestedAction = Literal["beds", "transport", "pharmacy", "expert", "sos"]


class ClinicalConsultRequest(BaseModel):
    """Request payload for a clinical consultation.

    Attributes:
        text: Clinical query or description of patient symptoms.
        phc_id: Unique identifier for the primary health centre. Defaults to "phc-purnia".
        lang: Preferred language representation code. Defaults to "hi-en".
    """

    text: str = Field(min_length=1, max_length=4000)
    phc_id: str = "phc-purnia"
    lang: str = "hi-en"


class HindiScriptRequest(BaseModel):
    """Request payload for converting or processing Hindi script/text.

    Attributes:
        text: Input text string to be converted or translated.
    """

    text: str = Field(min_length=1, max_length=1000)


class ClinicalFacts(BaseModel):
    """Extracted clinical facts from user input query.

    Attributes:
        age: Patient age in years, if present.
        sex: Patient gender/sex, if present.
        symptoms: List of extracted symptom strings.
        duration: Duration of symptoms, if mentioned.
        vitals: Key-value dictionary of vital signs.
        labs: Key-value dictionary of laboratory test results.
        comorbidities: List of identified pre-existing conditions.
        english_query: Standardized clinical query translated into English.
    """

    age: int | None = None
    sex: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    duration: str | None = None
    vitals: dict[str, str] = Field(default_factory=dict)
    labs: dict[str, str] = Field(default_factory=dict)
    comorbidities: list[str] = Field(default_factory=list)
    english_query: str


class Diagnosis(BaseModel):
    """Diagnostic impression and associated classification.

    Attributes:
        name: Clinical diagnosis or working assessment title.
        icd10: ICD-10 diagnostic classification code, if available.
        confidence: Estimated confidence score for the diagnosis (0.0 to 1.0).
    """

    name: str
    icd10: str | None = None
    confidence: float = 0.0


class ActionStep(BaseModel):
    """Sequential clinical recommendation or management step.

    Attributes:
        n: Step index number in sequence.
        title: Short title of the action step.
        detail: Detailed instructions for executing the step.
    """

    n: int
    title: str
    detail: str


class Referral(BaseModel):
    """Referral details for higher-center care.

    Attributes:
        required: Whether a referral to a higher-level facility is required.
        urgency: Urgency level of the referral ("urgent", "priority", or "routine").
        destination: Destination hospital or facility name.
        slip: Summary note or text for referral slip documentation.
        golden_hour_min: Target window in minutes for emergency referral/intervention.
    """

    required: bool
    urgency: Urgency = "routine"
    destination: str = ""
    slip: str = ""
    golden_hour_min: int | None = None


class Source(BaseModel):
    """Reference source from Standard Treatment Workflows (STW) or guidelines.

    Attributes:
        n: Reference source index.
        stw_title: Title of the source document or workflow.
        section: Specific section or heading within the source document.
        quote: Direct excerpt or relevant guideline text.
        pdf: Filename or URI of the reference PDF document.
    """

    n: int
    stw_title: str
    section: str = ""
    quote: str = ""
    pdf: str = ""


class RetrievalMeta(BaseModel):
    """Metadata regarding knowledge retrieval context.

    Attributes:
        chunk_count: Number of retrieved knowledge base chunks.
        top_score: Highest relevance score among retrieved chunks.
    """

    chunk_count: int
    top_score: float | None = None


class ClinicalCard(BaseModel):
    """Structured clinical decision support output card.

    Attributes:
        urgency: Overall clinical urgency level.
        assessment: Summary points of clinical assessment.
        diagnosis: Primary working diagnosis.
        steps: Recommended action steps for healthcare workers.
        do_nots: Contraindicated actions or critical warnings.
        referral: Referral decision and routing details.
        sources: Supporting STW/guideline references.
        suggested_actions: Suggested action shortcuts for downstream workflow.
        disclaimer: Standard medical disclaimer text.
        latency_ms: Processing latency in milliseconds.
        retrieval: Retrieval process metadata.
        fhir_id: Optional FHIR encounter/bundle resource identifier.
        model: Model name/version used for generating the card.
    """

    urgency: Urgency
    assessment: list[str]
    diagnosis: Diagnosis
    steps: list[ActionStep]
    do_nots: list[str]
    referral: Referral
    sources: list[Source]
    suggested_actions: list[SuggestedAction]
    disclaimer: str
    latency_ms: int = 0
    retrieval: RetrievalMeta
    fhir_id: str | None = None
    model: str | None = None


class RetrievedChunk(BaseModel):
    """Knowledge base text chunk retrieved via RAG search.

    Attributes:
        text: Text contents of the chunk.
        stw_title: Title of the origin standard treatment workflow document.
        section: Section name within the document.
        pdf: Filename of the source PDF document.
        page: Page number in the source PDF document.
        score: Relevance or similarity score.
    """

    text: str
    stw_title: str
    section: str = ""
    pdf: str = ""
    page: int | None = None
    score: float | None = None


class TransportDispatchRequest(BaseModel):
    """Request payload for dispatching emergency or routine medical transport.

    Attributes:
        kind: Vehicle category, either "ambulance" or "volunteer".
        need_oxygen: Whether oxygen support equipment is required in transport.
    """

    kind: Literal["ambulance", "volunteer"] | None = None
    need_oxygen: bool = True


class PharmacyDispatchRequest(BaseModel):
    """Request payload for dispatching medications from a pharmacy.

    Attributes:
        pharmacy_id: Unique identifier for the targeted pharmacy.
        meds: List of medication names requested for dispatch.
    """

    pharmacy_id: str
    meds: list[str] = Field(default_factory=list)


class SosRequest(BaseModel):
    """Request payload for triggering an emergency SOS signal.

    Attributes:
        reason: Purpose or nature of the alert ("security" or "community").
        note: Additional context or notes describing the emergency.
    """

    reason: Literal["security", "community"] = "community"
    note: str = ""


class ExpertConsultRequest(BaseModel):
    """Request payload for initiating a specialist or expert consultation.

    Attributes:
        case_summary: Summary of the clinical case provided to the expert.
    """

    case_summary: str = ""
