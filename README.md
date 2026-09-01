# ClinAssistIndia

Human-in-the-loop decision support for PHC workers: Hinglish consults grounded on official ICMR Standard Treatment Workflows, plus worker-triggered beds, ambulance, Jan Aushadhi, expert, and SOS actions.

Clinical answers are **not** canned. They come from Sarvam `sarvam-105b` plus a local Chroma index of ICMR STW PDFs. If `SARVAM_API_KEY` is missing, the UI still boots and clinical consult returns an error.

---

## Table of contents

1. [Project description](#project-description)
2. [How to reproduce](#how-to-reproduce)
3. [Architecture](#architecture)
4. [What problem it solves](#what-problem-it-solves)
5. [Test prompts](#test-prompts)
6. [Existing constraints](#existing-constraints)
7. [Future roadmap](#future-roadmap)

---

## Project description

ClinAssistIndia is a PHC case workspace for a lone medical officer in rural India. The worker types a Hinglish case (symptoms, vitals, labs). The clinical agent extracts facts, retrieves ICMR STW passages, and returns a structured card: urgency, assessment, ICD-10, step-by-step PHC actions, contraindications, and a referral slip.

Specialized agents **do not run on their own**. After the card, the worker taps **बेड**, **एम्बुलेंस**, **दवाई**, **एक्सपर्ट**, or **SOS**.

| Layer | What it is |
|---|---|
| UI | Next.js 15 PHC workspace (chat, cards, Leaflet map) |
| API | FastAPI orchestrator on `/v1/*` |
| Clinical | Sarvam `sarvam-105b` + Chroma MiniLM over ICMR STW PDFs |
| Hindi | Sarvam Mayura (`mayura:v1`) for Devanagari |
| Ops | Curated Purnia JSON (hospitals, ambulances, pharmacies, experts, SOS) |
| FHIR | Silent ABDM-style `Encounter` / `MedicationRequest` / `ServiceRequest` on disk |

Demo geography is **PHC Khajanchi Hat, Purnia, Bihar (PIN 854301)**.

---

## How to reproduce

**Need:** Python 3.11+, Node 18+, a [Sarvam](https://dashboard.sarvam.ai) API key.

GitHub clones this repo into **`clinassitInda`** (the repo slug). A default `git clone` does not create `clinassitindia-public`. This checkout uses **UI 3002** and **API 8002**. Do not bind 3000, 3001, 8000, or 8001.

```bash
git clone https://github.com/jonsnow14/clinassitInda.git
cd clinassitInda

cp .env.example .env
# set SARVAM_API_KEY=sk_...   (https://dashboard.sarvam.ai)

# 1) ICMR index (downloads official STW PDFs into data/icmr/pdfs, writes data/chroma)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.rag.ingest

# 2) API — port 8002
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002

# 3) UI — port 3002  (other terminal)
cd apps/web
npm ci
npm run dev
```

Open **http://127.0.0.1:3002**

Check the API before using the UI:

```bash
curl -s http://127.0.0.1:8002/v1/health
# required: "chroma_ready": true  AND  "sarvam_key_present": true
# if chroma_ready is false, ingest did not finish — do not open the UI yet
```

Next.js proxies `/v1/*` to `http://127.0.0.1:8002`. Skip ingest on later runs if `data/chroma` is already built. Use `npm ci` (the lockfile is in git); do not `npm install`.

Beds, ambulance, pharmacy, expert, and SOS are deterministic from `data/purnia/*.json`. The ICMR index is rebuilt locally by ingest. The clinical card is live Sarvam (`temperature` 0) plus Mayura — same prompt and key will not always print the same Hindi or ICD.

`?debug=1` on the UI shows the silent FHIR encounter id (not the JSON).

---

## Architecture

Two local processes: the Next.js workspace talks to FastAPI over same-origin `/v1/*`. Clinical RAG uses Sarvam + Chroma. Beds, transport, pharmacy, expert, and SOS read deterministic JSON, not the vector index. Vehicle movement is HTTP polling every 3 seconds, not GPS.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Next.js PHC workspace  (:3002)                       │
│   Clinical chat & card  ·  Mayura Hinglish hook  ·  Leaflet map          │
└──────────────┬──────────────────────────┬───────────────────┬────────────┘
               │ /v1/* rewrite            │ transliterate     │ poll 3s
               ▼                          ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        FastAPI orchestrator  (:8002)                     │
│  Clinical agent   Ops (beds/ambulance)   Pharmacy   Expert   SOS   FHIR  │
└──────────┬───────────────────────────────────────────────┬───────────────┘
           ▼                                               ▼
┌─────────────────────────────┐             ┌──────────────────────────────┐
│  Sarvam cloud               │             │  Local stores                │
│  sarvam-105b  (JSON card)   │             │  Chroma  (ICMR STW embeds)   │
│  mayura:v1    (Hindi)       │             │  data/purnia/*.json          │
└─────────────────────────────┘             │  apps/api/var/fhir/          │
                                            └──────────────────────────────┘
```

Clinical path: Hinglish in → Sarvam extract English facts → MiniLM retrieve ICMR passages → Sarvam grounded `ClinicalCard` → Mayura Hindi → silent FHIR write.

**Developer prompt skill (not on the live path).** [prompt-optimizer](https://skillpatch.dev/skill/prompt-optimizer) (SkillPatch, Sentry) is a **developer-only** LatentCode skill at `.latentcode/skills/prompt-optimizer/`. Use `/prompt-optimizer` in LatentCode to tighten `EXTRACT_SYSTEM` and `GENERATE_SYSTEM` in `apps/api/app/rag/clinical_agent.py` against an eval set. It does **not** rewrite the PHC worker’s note at request time. Live consult stays extract → Chroma → generate. Details: **[docs/architecture.md](docs/architecture.md#41-developer-prompt-optimizer)**.

Agents fire only from UI buttons / slash commands (`/clinical`, `/beds`, `/transport`, `/pharmacy`, `/expert`, `/sos`).

```
apps/api     FastAPI + RAG + agents
apps/web     Next.js PHC workspace
data/purnia  Curated ops JSON (in git)
data/icmr    STW PDFs (downloaded by ingest, not in git)
data/chroma  Vector index (built by ingest, not in git)
docs/        Architecture, problem statement, roadmap, design
.latentcode/skills/prompt-optimizer   Dev-only SkillPatch (EXTRACT_SYSTEM / GENERATE_SYSTEM)
```

Full module list, endpoints, and the five-step clinical pipeline: **[docs/architecture.md](docs/architecture.md)**.

---

## What problem it solves

A medical officer at a rural PHC is often alone, with a queue outside and the nearest cardiologist tens of kilometres away. Cases arrive in Hinglish. English-only guidelines and English-only models drop rural phrasing (`SOB 3 din se`).

ClinAssistIndia is for that desk:

1. **Clinical** — ICMR-grounded next steps at the PHC (not a chatbot essay).
2. **Beds** — nearby ICU / oxygen / general capacity from a local hospital list.
3. **Ambulance** — dispatch and a live-looking track to the PHC.
4. **Pharmacy** — Jan Aushadhi first, then courier simulation.
5. **Expert** — specialist directory and a consult request (no WebRTC in this build).
6. **SOS** — law-enforcement / volunteer alert record.

The worker stays in control. Output is decision support; treating judgment stays with the clinician.

Scenario write-up: **[docs/problem-statement.md](docs/problem-statement.md)**.

---

## Test prompts

Paste into the consult box, then tap the Hindi action chips. None of the ops agents run until you tap them.

**1. Golden path (NSTEMI / ACS)**

```
Patient 45M, SOB 3 din se, BP 160/100, sugar bhi hai, troponin slightly elevated. Kya karna chahiye?
```

Then: **बेड** → **एम्बुलेंस** → **दवाई** → **एक्सपर्ट** → **SOS**.

**2. STEMI-like chest pain**

```
55M, 2 ghante se tees chest pain, left arm ja raha hai, sweating, ECG pe ST elevation dikh raha hai. Abhi kya karna hai?
```

**3. Heart failure / breathlessness**

```
62F, known HF, raat ko saans phool rahi hai, legs sooj gaye, SpO2 90, BP 150/90. PHC pe kya karein, kab refer karein?
```

**4. Diabetes at the PHC**

```
50M, sugar 380, pyaas zyada, 2 din se kamzori, ketones nahi check hue. Admit karna chahiye kya?
```

**5. Hinglish-only (script / Mayura)**

```
bhaiya ko 3 din se bukhar aur khansi hai, bp 140/90, pehle se sugar ki dawai khata hai. icmr ke hisaab se kya protocol hai?
```

Expect: a structured card (not free prose), ICMR source lines, Hindi worker-facing text, and a debug encounter id with `?debug=1`. Card wording can vary across runs even with the same key.

---

## Existing constraints

| Piece | This build |
|---|---|
| ICMR STW PDFs → Chroma MiniLM | Real retrieval |
| Sarvam `sarvam-105b` extract + grounded card | Real API; needs `SARVAM_API_KEY` |
| Mayura Hindi | Real API; same key |
| Hospitals / pharmacies / experts / SOS (Purnia) | Curated local JSON, not live government feeds |
| Ambulance / courier movement | Simulated HTTP poll every 3s |
| WhatsApp, SMS, ABDM POST, WebRTC | **Not** in this build |
| FHIR | Written under `apps/api/var/fhir/`; not posted to ABDM |
| Ports | UI **3002**, API **8002** only |

Other limits:

- Decision support only, not a device or a diagnosis.
- Index coverage is the ingested STW PDFs (cardiology / ACS, HF, endocrinology), not all of ICMR.
- Embeddings are English MiniLM: Hinglish is extracted to English **before** retrieval.
- One-node demo: no auth, no multi-PHC, no production hosting.
- `data/chroma` and `data/icmr/pdfs` are generated locally and are not in git.
- Clinical consult is not bit-identical: Sarvam + Mayura can differ across runs at `temperature` 0.

---

## Future roadmap

Shipped for the POC: ICMR RAG clinical card, human-triggered beds / transport / pharmacy / expert / SOS, map polling, silent FHIR, Purnia sample data.

Next, in order:

1. Real notifications — WhatsApp / SMS for pharmacy enquiry and SOS, instead of in-app only.
2. Live ops feeds — hospital bed APIs / NHP-style directories instead of static JSON.
3. Real tracking — GPS or a message bus (Redis pub/sub), not 3s simulated polls.
4. Expert path — WebRTC (or a phone bridge) instead of a directory + stub consult.
5. ABDM — POST the FHIR bundle to a sandbox, not only disk.
6. Geography — more blocks than Purnia 854301; radius search when PIN misses.
7. Corpus — more STWs (snakebite, maternal, sepsis) still ICMR-grounded.
8. Agents orchestration and evaluation pipelines, continous performance monitoring and guardrails 

Principles that stay: human trigger, Sarvam for Indic input, ICMR for clinical text, Jan Aushadhi first, deterministic ops data.

Longer plan: **[docs/roadmap.md](docs/roadmap.md)**. Design sketch: **[docs/design/base-design.jpg](docs/design/base-design.jpg)**.
