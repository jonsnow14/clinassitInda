# ClinAssist India

ClinAssist India is an AI-powered, multilingual healthcare and clinical operations assistant. Designed to streamline medical triage, provide clinical guidance based on official protocols, and coordinate critical healthcare operations such as bed availability, emergency transport, and pharmacy supplies.

## 🚀 Features

*   **Clinical Assistant (RAG):** AI-driven clinical chat built on top of ICMR (Indian Council of Medical Research) guidelines using LlamaIndex.
*   **Operations Management:** Real-time lookup and management for hospitals, bed availability, and medical experts.
*   **Emergency Transport:** Geo-location-based ambulance routing and SOS escalation.
*   **Pharmacy Locator:** Search and manage nearby pharmacies and inventory.
*   **Multilingual Support:** Powered by Sarvam AI to bridge regional language barriers in Indian healthcare.
*   **FHIR Compliant:** Data models adhere to standard FHIR (Fast Healthcare Interoperability Resources) schemas.

## 🛠 Tech Stack

*   **Frontend:** Next.js (TypeScript), React, Tailwind CSS
*   **Backend:** FastAPI (Python), LlamaIndex (RAG pipeline)
*   **AI / ML:** Sarvam AI (translation/NLP), Local Vector Storage for RAG
*   **Data Standards:** FHIR (Fast Healthcare Interoperability Resources)

## 📁 Project Structure

```text
lf-hackathon/
├── backend/          # FastAPI backend application
│   ├── app/          # API routes, services (RAG, Sarvam, Geo), and FHIR models
│   └── scripts/      # Data ingestion scripts (e.g., ingest.py for LlamaIndex)
├── frontend/         # Next.js web application
│   └── src/          # React components (ClinicalChat, OpsPanel, Pharmacy, SOS)
├── data/             # Source datasets
│   ├── guidelines/   # Clinical guidelines (e.g., ICMR txt files)
│   └── ops/          # JSON data for hospitals, pharmacies, ambulances, experts
├── docs/             # Project documentation, roadmap, and design diagrams
└── var/storage/      # Generated vector store and index data (gitignored)
```

## 🚦 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python (3.9+)

### 1. Setup the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env and add your respective API keys (e.g., LLM, Sarvam AI)

# Ingest data (builds the RAG vector store)
python scripts/ingest.py

# Run the FastAPI server
fastapi dev app/main.py
# Server runs on http://127.0.0.1:8000
```

### 2. Setup the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
# App runs on http://localhost:3000
```

## 📖 Documentation

Detailed documentation and design thoughts can be found in the `docs/` directory:
*   [Problem Statement](docs/problem-statement.md)
*   [Roadmap](docs/roadmap.md)
*   [Base Design / Architecture](docs/design/clinassistindia-base-design.jpg)

## 📜 License

This project is licensed under the MIT License.
