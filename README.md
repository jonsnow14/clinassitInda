# ClinAssistIndia

PHC worker case workspace: **Sarvam** Hinglish consult grounded on a **real ICMR STW Chroma index**, plus human-triggered beds / ambulance / Jan Aushadhi / expert / SOS agents.

Clinical answers are **not** canned. If `SARVAM_API_KEY` is missing, the UI still boots and clinical consult returns an error.

## Run

```bash
export SARVAM_API_KEY=sk_...     # https://dashboard.sarvam.ai
cp .env.example .env             # optional; same key there

# 1) ICMR index (downloads official STW PDFs)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.rag.ingest

# 2) API  — port 8001 (do not use 8000)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# 3) UI — port 3001 (do not use 3000)
cd apps/web
npm install
npm run dev
```

Open **http://127.0.0.1:3001**

Ports are fixed: **UI 3001**, **API 8001**. Do not bind 3000 or 8000. Next.js proxies `/v1/*` to `http://127.0.0.1:8001`.

## Golden prompt

```
Patient 45M, SOB 3 din se, BP 160/100, sugar bhi hai, troponin slightly elevated. Kya karna chahiye?
```

Then tap **बेड**, **एम्बुलेंस**, **दवाई**, **एक्सपर्ट**, **SOS**. None of those fire unless you tap them.

`?debug=1` shows the silent FHIR encounter id (not the JSON).

## What is real vs mocked

| Piece | Status |
|---|---|
| ICMR STW PDFs → Chroma MiniLM index | Real retrieval |
| Sarvam `sarvam-105b` Hinglish extract + grounded card | Real API |
| Hospital / pharmacy / expert / SOS directories (Purnia) | Curated local JSON |
| Ambulance / courier movement | Simulated HTTP poll (3s) |
| WhatsApp, SMS, ABDM POST, WebRTC | Not in this build |

## Layout

```
apps/api     FastAPI + RAG + agents
apps/web     Next.js PHC workspace
data/purnia  Curated ops JSON (in git)
data/icmr    STW PDFs (downloaded by ingest, not in git)
data/chroma  Vector index (built by ingest, not in git)
docs/        Architecture, problem statement, roadmap, design
```

See `docs/architecture.md`, `docs/problem-statement.md`, and `docs/roadmap.md`.
