# ClinAssistIndia System Architecture

`ClinAssistIndia` is a human-in-the-loop decision support workspace designed for Primary Health Centre (PHC) healthcare workers and Medical Officers in rural India. It combines Sarvam AI Indic language models, Retrieval-Augmented Generation (RAG) over official ICMR Standard Treatment Workflows (STWs), deterministic operational databases, dynamic mapping, and Ayushman Bharat Digital Mission (ABDM) FHIR compliance.

---

## 1. High-Level Architecture Overview

The system consists of a Next.js frontend workspace communicating with an asynchronous Python FastAPI backend orchestrator over REST endpoints. Specialized sub-agents are strictly human-triggered from the PHC worker interface.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             Next.js Frontend (Port 3002)                         │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌────────────────────┐  │
│  │ Clinical Chat & Card  │   │   Mayura Script Hook  │   │  Leaflet Map View  │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └─────────┬──────────┘  │
└──────────────┼───────────────────────────┼─────────────────────────┼─────────────┘
               │                           │                         │
               │ HTTP Proxy (/v1/*)        │ Transliterate           │ Polling (3s)
               ▼                           ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend (Port 8002)                           │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌────────────────────┐  │
│  │    Clinical Agent     │   │   Operations Agent    │   │  Pharmacist Agent  │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └─────────┬──────────┘  │
│  ┌───────────┴───────────┐   ┌───────────┴───────────┐                        │  │
│  │ Expert & Security SOS │   │ ABDM FHIR Generator   │                        │  │
│  └───────────────────────┘   └───────────────────────┘                        │  │
└──────┬───────────────────────────────────┬────────────────────────────────────┘
       │                                   │
       ▼                                   ▼
┌───────────────────────────────┐   ┌───────────────────────────────────────────┐
│     Sarvam AI Cloud APIs      │   │          Local Data Stores                │
│ ┌───────────────────────────┐ │   │ ┌───────────────────┐ ┌─────────────────┐ │
│ │ sarvam-105b (JSON Comple) │ │   │ │ Chroma Vector DB │ │ Purnia Ops JSON │ │
│ ├───────────────────────────┤ │   │ │ (ICMR STW Embeds) │ │ (Beds/Transport)│ │
│ │ mayura:v1 (Translate)     │ │   │ └───────────────────┘ └─────────────────┘ │
│ └───────────────────────────┘ │   │ ┌───────────────────┐                     │
└───────────────────────────────┘   │ │ ABDM FHIR Store   │                     │
                                    │ │ (data/fhir/*.json)│                     │
                                    │ └───────────────────┘                     │
                                    └───────────────────────────────────────────┘
```

---

## 2. Core Architecture Principles

1. **Human-in-the-Loop Execution**: Specialized agents (Bed finder, Transport dispatch, Pharmacy stock, Expert tele-consult, Security SOS) do not run autonomously. They execute strictly upon explicit worker selection via UI buttons or slash commands (`/beds`, `/transport`, `/pharmacy`, `/expert`, `/sos`).
2. **Native Indic Language Understanding**: Raw Hinglish and transliterated rural inputs are processed directly via Sarvam AI (`sarvam-105b` for clinical extraction and `mayura:v1` for Hindi translation), removing language barriers for PHC staff.
3. **ICMR Guidelines Grounding**: Clinical recommendations are strictly grounded in retrieved ICMR Standard Treatment Workflow PDF passages.
4. **Deterministic Operational State**: Hospital bed counts, vehicle locations, and pharmacy stock queries query clean, local geospatial JSON datasets rather than relying on unstructured vector search.
5. **ABDM FHIR Compliance**: Consultations automatically and silently generate HL7 FHIR R4 compliant Bundles (`Encounter`, `MedicationRequest`, `ServiceRequest`) on the backend for seamless inter-facility referral integration.

---

## 3. Python API Backend (`apps/api`)

The backend is built with FastAPI and runs on Uvicorn on **Port 8002**.

### 3.1 Service Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/health` | Service health status, vector store readiness, active model, and base PHC coordinates |
| `POST` | `/v1/script/hindi` | Transliterates/translates Roman Hinglish into Hindi Devanagari script via Sarvam Mayura |
| `POST` | `/v1/clinical/consult` | Main RAG endpoint; returns structured `ClinicalCard` and writes FHIR bundle |
| `GET` | `/v1/beds` | Searches regional hospital directory (`hospitals.json`) filtered by bed requirement (`icu`, `oxygen`, `general`) |
| `GET` | `/v1/transport` | Lists emergency ambulances and community volunteer transport vehicles |
| `POST` | `/v1/transport/dispatch` | Dispatches transport vehicle and initializes trip trajectory |
| `GET` | `/v1/transport/{trip_id}/track` | Tracks real-time vehicle movement, polyline route, and updated ETA |
| `GET` | `/v1/pharmacy` | Searches regional pharmacy stock, strictly prioritizing Jan Aushadhi Kendras (PMBJK) |
| `POST` | `/v1/pharmacy/dispatch` | Dispatches medicine courier delivery from target pharmacy |
| `GET` | `/v1/courier/{trip_id}/track` | Tracks active medicine courier location and delivery progress |
| `POST` | `/v1/sos` | Raises emergency SOS alert for local law enforcement or volunteer networks |
| `GET` | `/v1/sos/{sos_id}` | Checks status of an active SOS signal |
| `GET` | `/v1/experts` | Fetches available specialist physicians for tele-consultation |
| `POST` | `/v1/experts/{expert_id}/consult` | Initiates tele-consultation connection with chosen specialist |

### 3.2 Backend Modules and Subsystems

- **`app.rag.clinical_agent`**: Coordinates the 2-step clinical pipeline (Fact extraction -> ICMR passage retrieval -> Grounded decision generation -> Devanagari translation -> FHIR bundle persistence).
- **`app.rag.retriever`**: Executes vector similarity search against local ChromaDB (`all-MiniLM-L6-v2` embeddings) with distance threshold filtering (`SCORE_FLOOR_DISTANCE = 1.35`).
- **`app.rag.ingest`**: Downloads official ICMR PDF workflows, extracts text chunks, computes vector embeddings, and populates persistent Chroma collection at `data/chroma`.
- **`app.sarvam_client`**: Native HTTP client interfacing with Sarvam AI API endpoints (`/v1/chat/completions`) for structured JSON completion with Pydantic schemas (`FACTS_SCHEMA`, `CARD_SCHEMA`).
- **`app.mayura`**: Wraps Sarvam Mayura translation API (`/translate`), handling text chunking (`§§` separator), Devanagari detection ratios (`deva_ratio`), and recursive payload translation (`hindi_card`, `hindi_payload`).
- **`app.agents.ops`**: Handles hospital bed availability queries and ambulance dispatch.
- **`app.agents.pharmacy`**: Manages Jan Aushadhi (PMBJK) stock verification and courier dispatch.
- **`app.agents.security`**: Manages security and community emergency SOS alerts.
- **`app.agents.expert`**: Manages specialist directories and tele-consultation requests.
- **`app.simulate`**: Simulation engine that generates intermediate vehicle coordinates along a route polyline, updating position and ETA across periodic polling requests.
- **`app.geo`**: Implements Haversine distance calculations and defines base PHC coordinates (Purnia, Bihar).
- **`app.fhir`**: Constructs HL7 FHIR R4 JSON bundles (`Encounter`, `MedicationRequest`, `ServiceRequest`) and persists them locally to `data/fhir/<encounter_id>.json`.

---

## 4. Clinical RAG & Sarvam AI Integration

The clinical consultation flow overcomes the "Hinglish-to-Vector" semantic gap using a two-step pipeline:

```
[ Hinglish Consultation Input ]
               │
               ▼
┌──────────────────────────────────────────────┐
│  Step 1: Sarvam Extraction (sarvam-105b)     │
│  - Extracts age, sex, symptoms, vitals, labs │
│  - Generates standardized English query      │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Step 2: Vector Retrieval (ChromaDB)         │
│  - Queries MiniLM index with English query   │
│  - Retrieves top ICMR STW PDF passages       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Step 3: Grounded Generation (sarvam-105b)   │
│  - Combines facts + ICMR passages            │
│  - Generates structured ClinicalCard         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Step 4: Mayura Translation (mayura:v1)      │
│  - Converts worker prose into Devanagari     │
│  - Preserves medical codes (ICD-10, dosage)  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Step 5: ABDM FHIR Bundle Generation         │
│  - Writes Encounter, Meds, ServiceRequest    │
│  - Stores silently at data/fhir/*.json       │
└──────────────────────────────────────────────┘
```

---

## 5. Next.js Frontend Workspace (`apps/web`)

The frontend is built with Next.js 15 App Router, React 19, and TailwindCSS running on **Port 3002**.

### 5.1 Architecture & Page Structure

- **`app/page.tsx`**: Main interactive PHC workspace.
  - Maintains consultation state, message history, active agent mode, and live tracking payloads.
  - Features typing debouncer (`400ms`) that calls Sarvam Mayura for real-time Roman Hinglish to Devanagari transliteration.
  - Supports slash commands (`/clinical`, `/beds`, `/transport`, `/pharmacy`, `/expert`, `/sos`) for fast keyboard navigation.
- **`components/Cards.tsx`**: Structured UI card renderers:
  - `ClinicalCardView`: Urgency indicator, assessment bullets, primary diagnosis with ICD-10 tag, step-by-step action plan, contraindications, referral summary, source references, and workflow action chips.
  - `BedsCard`: Hospital list displaying ICU/Oxygen bed availability and distance.
  - `TransportCard`: Live transport tracking card with status badge, vehicle driver details, and ETA indicator.
  - `PharmacyCard`: PMBJK and local pharmacy stock view with one-click courier dispatch.
  - `ExpertCard`: Specialist directory with tele-consult connect trigger.
  - `SosCard`: Emergency dispatch acknowledgement.
- **`components/MapView.tsx`**: Client-only (`ssr: false`) interactive map built on Leaflet and OpenStreetMap.
  - Renders base PHC marker, nearby hospital markers color-coded by STEMI/NSTEMI acceptance, active vehicle location marker, and dynamic route polylines.
- **`lib/api.ts`**: Client API wrapper communicating with `/v1/*` proxy endpoints.

---

## 6. Integrations & Third-Party Dependencies

1. **Sarvam AI APIs**:
   - `sarvam-105b`: Employed via `/v1/chat/completions` with JSON schema enforcement for entity extraction and clinical decision generation.
   - `mayura:v1`: Employed via `/translate` (`code-mixed` mode, `fully-native` output script) for English/Hinglish to Hindi translation.
2. **Leaflet & OpenStreetMap**:
   - Client-side interactive mapping library integrated without server-side rendering issues via Next.js dynamic import.
3. **ChromaDB & Sentence Transformers**:
   - Embedded local vector store using `all-MiniLM-L6-v2` embeddings for vector search over ICMR PDF text chunks.
4. **HL7 FHIR R4**:
   - Native Python serialization generating valid ABDM FHIR Bundles containing `Encounter`, `MedicationRequest`, and `ServiceRequest` resource schemas.

---

## 7. Operational Data Stores

For POC reliability and edge deployment feasibility, operational registries are maintained in local JSON stores under `data/purnia/`:

- **`hospitals.json`**: Directory of regional facilities (e.g., Sadar Hospital Purnia, Max7 Hospital) with bed counts (ICU, Oxygen, General) and NSTEMI capability flags.
- **`ambulances.json`**: Ambulance and volunteer vehicle fleet details, driver contacts, oxygen equipment flags, and starting coordinates.
- **`pharmacies.json`**: Local pharmacies strictly highlighting Jan Aushadhi Kendras (PMBJK) with stock availability for essential medicines (Aspirin, Clopidogrel, Atorvastatin, Heparin).
- **`experts.json`**: Specialist registry (Cardiologists, Physicians) for tele-consultation.
- **`sos_contacts.json`**: Local law enforcement and emergency response contacts.

---

## 8. Deployment and Networking Model

### 8.1 Network Routing & Proxying

- **UI Port**: `3002` (Next.js development server)
- **API Port**: `8002` (Uvicorn / FastAPI server)
- Next.js proxies all `/v1/*` frontend requests directly to `http://127.0.0.1:8002` as configured in `apps/web/next.config.ts`:

```typescript
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/v1/:path*",
        destination: "http://127.0.0.1:8002/v1/:path*",
      },
    ];
  },
};
```

- FastAPI enables CORS specifically for `http://localhost:3002` and `http://127.0.0.1:3002`.

### 8.2 Execution & Environment Requirements

1. **Environment Configuration**:
   - Set `SARVAM_API_KEY` in root `.env` or environment export.
2. **Ingestion Step**:
   - Run `python -m app.rag.ingest` inside `apps/api` to download ICMR STW PDFs and generate the local Chroma vector index.
3. **Local Microservice Architecture**:
   - Both backend and frontend run locally on the PHC node. External connectivity is required solely for Sarvam AI inference API calls, allowing local operational databases and FHIR generation to function resiliently.
