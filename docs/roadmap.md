# ClinAssistIndia - Implementation Roadmap

**Status:** `BRAINSTORMING`  
**Target User:** Frontline Healthcare Workers / Medical Officers at Primary Health Centres (PHC) in Rural India  
**Core Architecture:** Human-Triggered Agentic RAG Assistant powered by Sarvam Reasoning Models + ICMR Vector RAG + ABDM FHIR Engine

---

## 1. Vision & Core Principles

ClinAssistIndia is an intelligent, human-in-the-loop decision support system for PHC workers. 

### Key Principles:
1. **Human-in-the-Loop Execution:** Agents DO NOT run autonomously or unsupervised. Specialized agents execute ONLY when explicitly triggered by the PHC worker via UI actions or commands.
2. **Sarvam AI Reasoning:** Native Hinglish and Indic language understanding directly via Sarvam AI models to bridge the rural healthcare communication gap.
3. **Strict Evidence-Based Guidance:** Clinical recommendations are strictly grounded in ICMR 2022 Guidelines and verified medical datasets.
4. **Jan Aushadhi First (Affordability):** The Pharmacist agent strictly prioritizes Pradhan Mantri Bhartiya Janaushadhi Kendras (PMBJK) mapped by PIN code/block before suggesting private pharmacies.
5. **Deterministic Operations:** Hospital bed search, transportation tracking, and pharmacy stock queries rely on clean relational/geospatial databases rather than unsupervised vector updates.
6. **ABDM Compliance:** Automatic generation of FHIR-compliant (`Encounter`, `MedicationRequest`, `ServiceRequest`) JSON payloads for seamless referral integration.

---

## 2. Multi-Agent System Architecture

```
[ PHC Health Worker ] ──(Explicit Trigger)──► [ Frontend UI (Next.js) ]
                                                     │
                                                     ▼
                                          [ FastAPI Router Backend ]
                                                     │
        ┌──────────────────────┬─────────────────────┼──────────────────────┐
        ▼                      ▼                     ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Clinical    │       │  Operations  │       │  Pharmacist  │       │  Security/   │
│   Agent      │       │    Agent     │       │    Agent     │       │  SOS Agent   │
└──────┬───────┘       └──────┬───────┘       └──────┬───────┘       └──────┬───────┘
       │                      │                      │                      │
       ▼                      ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Sarvam AI + │       │ Nearby Beds  │       │ Stock Check  │       │ Volunteer &  │
│  ICMR Chroma │       │ SQL/JSON DB  │       │ & Courier    │       │ Police SOS   │
└──────────────┘       └──────────────┘       └──────────────┘       └──────────────┘
```

---

## 3. Technology Stack & Architecture Decisions [Status: BRAINSTORMING]

### Selected Stack
- **Frontend:** Next.js (React), TailwindCSS, Leaflet/OpenStreetMap.
- **Backend Orchestrator:** FastAPI (Python).
- **Agent/RAG Framework:** LlamaIndex.
- **Vector Database (Clinical Data):** ChromaDB (Local/Embedded).
- **Operational Database (State & Geospatial):** SQLite (Local) / Python DataFrames.
- **LLM / Reasoning Model:** Sarvam AI.

### Architectural Decisions & Justifications

#### 1. Why FastAPI for Orchestration (vs. CrewAI/AutoGen)?
We decided against autonomous multi-agent frameworks (like CrewAI or AutoGen) because our agents are **human-triggered**. The PHC worker explicitly calls the required agent (e.g., `/clinical`, `/pharmacy`). A simple, asynchronous FastAPI router provides a cleaner, faster, and more predictable orchestration layer for the frontend to interact with, avoiding the latency and unpredictability of autonomous agents talking to each other.

#### 2. Why LlamaIndex (vs. LangChain)?
While LangChain is a popular general-purpose framework, **LlamaIndex** is purpose-built specifically for Retrieval-Augmented Generation (RAG) over documents. It offers superior out-of-the-box PDF parsing, hierarchical chunking, and indexing strategies, which are critical for extracting precise medical rules from complex ICMR Guideline PDFs.

#### 3. Why ChromaDB (vs. Pinecone/Weaviate/PostgreSQL)?
Cloud-based vector databases (Pinecone, Weaviate) introduce network latency, require API key management, and add risk during a live hackathon demo if internet connectivity drops. **ChromaDB** runs entirely locally and embedded within the Python/FastAPI process. It requires zero complex setup, runs fast, and persists data to a local folder (`./chroma_db`), making it bulletproof for our POC.

#### 4. Why SQLite for Operations (vs. Vector DBs)?
We made a critical architectural decision **not** to use a Vector DB for operational data (hospital beds, ambulance locations, pharmacy stock). Vector DBs are designed for semantic similarity, not real-time state management. 
For tracking available beds or finding the nearest Jan Aushadhi Kendra by PIN code, we need deterministic, structured queries. For a 48-hour POC, setting up a heavy spatial DB like PostGIS is overkill. **SQLite** (or in-memory Pandas dataframes) combined with Python's geospatial libraries (Haversine distance) provides fast, accurate, and manageable state tracking.

#### 5. Why Sarvam AI for Reasoning?
Relying on standard English LLMs requires building a clunky two-step translation pipeline (Hinglish -> English -> DB Query). **Sarvam AI** specializes in native Indic languages and Hinglish. By routing the PHC worker's raw input directly to Sarvam, we natively extract clinical intent ("SOB 3 din se" -> Dyspnea for 3 days) without translation loss, vastly simplifying the RAG pipeline.

---

## 4. Operational Risk Mitigations [Status: BRAINSTORMING]

To ensure we deliver a working, robust demo within 48 hours, we have identified the following operational fail points and adopted specific mitigation strategies:

1. **The "Hinglish-to-Vector" Retrieval Gap:**
   * **Risk:** Standard embedding models require English to match ICMR PDFs accurately. Passing raw Hinglish directly into LlamaIndex's retriever will yield poor semantic matches.
   * **Mitigation:** Enforce a strict pipeline within the Clinical Agent. Step 1: Sarvam AI translates/structures the Hinglish prompt into a formal English clinical query. Step 2: Pass the structured English output to the LlamaIndex retriever.


2. **ABDM FHIR JSON Hallucinations:**
   * **Risk:** Asking an LLM to generate complex, deeply nested FHIR JSON often results in syntax errors or missing required schemas, breaking the UI.
   * **Mitigation:** Do not use the LLM for raw JSON generation. Use the LLM to extract specific variables (Diagnosis, ICD-10, Medication). Use a Python Pydantic model or Jinja2 template on the backend to inject these variables into a hardcoded, validated FHIR schema.


3. **Real-Time Tracking WebSocket Overhead:**
   * **Risk:** Implementing true WebSockets for ambulance/courier tracking is time-consuming and prone to connection drops during a live demo.
   * **Mitigation:** Use HTTP polling instead. The Next.js frontend will use `setInterval` to fetch coordinates from a fast FastAPI endpoint every 3 seconds, simulating real-time movement seamlessly without WebSocket complexity.

4. **Jan Aushadhi PIN Code Misses:**
   * **Risk:** A strict PIN code match (`WHERE pincode = X`) will fail if the nearest Jan Aushadhi Kendra is in an adjacent PIN code just 2km away.
   * **Mitigation:** Include approximate Lat/Lng coordinates in the SQLite database for pharmacies and hospitals. Use Python's `geopy` library to execute a radius search (e.g., `< 10km`) rather than string-matching PIN codes.

5. **UI Over-Engineering:**
   * **Risk:** Spending too much time building a complex dashboard rather than connecting the core agents.
   * **Mitigation:** Build a straightforward "WhatsApp-style" chat interface focused on slash commands (`/clinical`, `/beds`, `/pharmacy`). Map tracking and FHIR payloads will be simple slide-out side panels.

## 4.  Action Plan for Operational Risk Mitigations [Status: BRAINSTORMING]

1. **The "Hinglish-to-Vector" Retrieval Gap:**
   * **Action Plan:** Enforce a strict two-step pipeline. Step 1: Sarvam AI translates/structures the Hinglish prompt into a formal English clinical query. Step 2: Pass the structured English output to the LlamaIndex retriever.
2. **ABDM FHIR JSON Hallucinations:**
   * **Action Plan:** Drop the JSON output feature from the UI entirely. The end-user PHC worker has no immediate use for raw JSON. For technical analysis and interoperability proof, the JSON payload will be generated securely on the backend (using Pydantic/Jinja2 templates) and stored silently in the backend database.
3. **Real-Time Tracking WebSocket Overhead:**
   * **Action Plan:** Create a mock Real-Time Tracking (RTT) / alert system for the POC. The POC UI will use simple HTTP polling (`setInterval`) to simulate live movement. Document the roadmap for full Phase II implementation (handling connection drops, state management, Redis Pub/Sub, and CORS issues).
4. **Jan Aushadhi PIN Code Misses:**
   * **Action Plan:** For the POC, curate a small, highly accurate sample of data matching PHCs with Jan Aushadhi Kendras in **Purnia, Bihar (PIN 854301)**. If data compilation for Purnia is poor, fallback to Satara, Maharashtra. Document bottlenecks for full-scale implementation (e.g., expanding the search radius when an exact PIN match fails).
5. **UI Over-Engineering:**
   * **Action Plan:** Park complex UI design for now. Design a simple, functional web-based UI where the PHC worker can enter a query and get a response. UI specifics will be fleshed out once backend agents are functional. 

---


## 5. Implementation Roadmap (48-Hour Hackathon)

### Phase 0: Foundations & Data Preparation [Status: COMPLETED]
- [x] Scaffold FastAPI backend and Next.js frontend directory structure.
- [x] Ingest ICMR Clinical Guidelines PDFs (Acute Coronary Syndrome, Hypertension, Diabetes, Snakebite) into ChromaDB vector store. (Pivoted to Mock RAG due to sandbox limits).
- [x] Curate synthetic static datasets for local healthcare infrastructure (`hospitals.json`, `ambulances.json`, `pharmacies.json`) mapping specifically to **Purnia, Bihar (PIN 854301)**.
- [x] Define ABDM FHIR schema templates (`Encounter`, `MedicationRequest`, `DiagnosticReport`) for backend-only generation.

### Phase 1: Clinical RAG Agent & Sarvam AI Integration [Status: COMPLETED]
- [x] Integrate Sarvam AI reasoning API for Hinglish query processing and medical entity extraction (Mocked intent router built).
- [x] Implement Vector RAG retriever against ICMR ChromaDB embeddings using the two-step (Hinglish -> English) pipeline.
- [x] Construct clinical response formatter (Diagnosis, ICD-10 code, Immediate Action Steps, DO NOTs, and Golden Hour warnings).
- [x] Implement ABDM FHIR JSON generator (Backend storage only, removed from UI rendering).

### Phase 2: Operations & Transport Agent (Human-Triggered) [Status: COMPLETED]
- [x] Build `/beds` trigger: Radius-based filter query against `hospitals.json` for available ICU/Oxygen beds.
- [x] Build `/transport` trigger: Nearest available ambulance/volunteer vehicle matching.
- [x] Implement WebSocket / Interval mock location engine for real-time "Swiggy-style" ambulance tracking on UI map.

### Phase 3: Pharmacist & Security SOS Agent [Status: COMPLETED]
- [x] Build `/pharmacy` trigger: Stock inquiry prioritizing Jan Aushadhi (PMBJK) via PIN code mapping & volunteer courier route dispatch.
- [x] Build `/sos` trigger: Emergency alert broadcasting to local law enforcement & volunteer network (UI Icon added for future API hookup).
- [x] Implement live tracking UI for medicine delivery volunteer.

### Phase 4: UI Polish & End-to-End Demo Scenario [Status: IN PROGRESS]
- [x] Build high-contrast, mobile-friendly PHC dashboard UI.
- [x] Test complete Scenario 1 end-to-end: 45M NSTEMI chest pain case in rural Bihar (Purnia).
- [ ] Record demo video & finalize pitch deck.

---

## 6. Potential Data Sources for POC

1. **Clinical Guidelines (RAG):**
   - ICMR Guidelines for Management of Acute Coronary Syndrome (2022)
   - ICMR Standard Treatment Workflows (STWs) for Primary Care
   - MIMIC-IV Open Clinical Summaries (Synthetic abstraction)
2. **Interoperability Standards:**
   - Ayushman Bharat Digital Mission (ABDM) FHIR Profiles
   - HL7 FHIR R4 Specification
3. **Infrastructure & Geospatial Data (Mocked for POC):**
   - National Health Portal (NHP) Hospital Directory Schema
   - PMBJP Jan Aushadhi Kendra Directory (Pincode/Block wise mapping)
   - OpenStreetMap / Leaflet mock coordinates around rural Bihar (Primary Test Target: Purnia, Bihar - PIN 854301. Fallback: Satara, Maharashtra)
