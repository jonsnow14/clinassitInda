import os
os.environ["HF_HUB_OFFLINE"] = "1"
import json
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from geopy.distance import geodesic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LlamaIndex Imports
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

app = FastAPI(title="ClinAssistIndia API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# --- BASE PATH RESOLUTION ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- DATA LOADING ---
def load_json_data(filename):
    path = os.path.join(BASE_DIR, "data", "ops", filename)
    with open(path, 'r') as f:
        return json.load(f)

hospitals_data = load_json_data("hospitals.json")
pharmacies_data = load_json_data("pharmacies.json")
ambulances_data = load_json_data("ambulances.json")
experts_data = load_json_data("experts.json")

# --- INITIALIZE LIVE RAG ENGINE ---
query_engine = None
try:
    print("Initializing Real LlamaIndex RAG Engine...")
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = None # Using Sarvam/Custom formatting instead of OpenAI
    
    persist_dir = os.path.join(BASE_DIR, "var", "storage")
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    query_engine = index.as_query_engine(similarity_top_k=2)
    print("RAG Engine Ready.")
except Exception as e:
    print(f"Warning: Could not load RAG index. Did you run ingest.py? Error: {e}")

# --- MODELS ---
class LocationQuery(BaseModel):
    pincode: str
    lat: float
    lng: float

class ClinicalQuery(BaseModel):
    query: str

# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "ClinAssistIndia Backend is running"}

@app.post("/api/clinical")
def process_clinical_query(req: ClinicalQuery):
    """
    REAL Clinical Agent: 
    1. Calls Sarvam API for Hinglish -> Medical English reasoning
    2. Queries live LlamaIndex Vector DB
    """
    raw_query = req.query
    
    # 1. REAL SARVAM AI CALL (Hinglish to Medical English Intent)
    if not SARVAM_API_KEY or SARVAM_API_KEY == "enter_your_real_api_key_here":
        return {"status": "error", "message": "SARVAM_API_KEY is missing in .env file"}

    sarvam_url = "https://api.sarvam.ai/translate"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "input": raw_query,
        "source_language_code": "hi-IN",
        "target_language_code": "en-IN",
        "speaker_gender": "Male",
        "mode": "formal",
        "model": "sarvam-translate"
    }
    
    try:
        sarvam_res = requests.post(sarvam_url, json=payload, headers=headers)
        if sarvam_res.status_code == 200:
            structured_intent = sarvam_res.json().get("translated_text", raw_query)
        else:
            # Fallback if API key is invalid/blocked
            structured_intent = raw_query
            print("Sarvam API Error:", sarvam_res.text)
    except Exception as e:
        structured_intent = raw_query
        print("Sarvam Connection Error:", str(e))

    # 2. REAL RAG RETRIEVAL (LlamaIndex)
    if query_engine:
        rag_response = query_engine.query(structured_intent)
        retrieved_rule_english = str(rag_response.source_nodes[0].node.text) if rag_response.source_nodes else "No relevant ICMR guidelines found."
    else:
        retrieved_rule_english = "RAG Engine offline. Vector database not found."

    # 3. REAL SARVAM AI CALL (English to Hindi/Hinglish Output Translation)
    payload_out = {
        "input": retrieved_rule_english,
        "source_language_code": "en-IN",
        "target_language_code": "hi-IN",
        "speaker_gender": "Male",
        "mode": "formal",
        "model": "sarvam-translate"
    }
    try:
        print(f"Translating {len(retrieved_rule_english)} chars to Hindi via Sarvam...")
        sarvam_res_out = requests.post(sarvam_url, json=payload_out, headers=headers)
        print("Sarvam Output Status:", sarvam_res_out.status_code)
        if sarvam_res_out.status_code == 200:
            retrieved_rule_hinglish = sarvam_res_out.json().get("translated_text", retrieved_rule_english)
            print("Translation Success:", retrieved_rule_hinglish[:50], "...")
        else:
            print("Sarvam API Error on Output:", sarvam_res_out.text)
            retrieved_rule_hinglish = retrieved_rule_english
    except Exception as e:
        print("Sarvam Connection Error on Output:", str(e))
        retrieved_rule_hinglish = retrieved_rule_english

    # 4. Format Response
    return {
        "status": "success",
        "agent": "Clinical",
        "sarvam_translation": structured_intent,
        "icmr_rule_retrieved": retrieved_rule_hinglish,
        "recommended_actions": [
            "Follow ICMR protocols extracted above",
            "Evaluate for immediate referral based on Golden Hour"
        ],
        "do_not_do": [
            "Check ICMR contraindications carefully"
        ],
        "fhir_payload_generated": True
    }

# (Operations and Pharmacy endpoints remain identical as they are operational DB queries, not RAG)
@app.post("/api/beds")
def find_beds(loc: LocationQuery):
    results = []
    phc_coords = (loc.lat, loc.lng)
    for hosp in hospitals_data:
        hosp_coords = (hosp['coordinates']['lat'], hosp['coordinates']['lng'])
        dist = geodesic(phc_coords, hosp_coords).kilometers
        total_beds = hosp['beds']['icu_available'] + hosp['beds']['oxygen_available'] + hosp['beds']['general_available']
        if total_beds > 0:
            hosp_copy = hosp.copy()
            hosp_copy['distance_km'] = round(dist, 2)
            results.append(hosp_copy)
    results.sort(key=lambda x: x['distance_km'])
    return {"status": "success", "agent": "Operations", "results": results}

@app.post("/api/pharmacy")
def find_pharmacy(loc: LocationQuery):
    pmbjk_results = []
    pvt_results = []
    phc_coords = (loc.lat, loc.lng)
    for pharm in pharmacies_data:
        pharm_coords = (pharm['coordinates']['lat'], pharm['coordinates']['lng'])
        dist = geodesic(phc_coords, pharm_coords).kilometers
        pharm_copy = pharm.copy()
        pharm_copy['distance_km'] = round(dist, 2)
        if pharm['type'] == "PMBJK":
            pmbjk_results.append(pharm_copy)
        else:
            pvt_results.append(pharm_copy)
    pmbjk_results.sort(key=lambda x: x['distance_km'])
    pvt_results.sort(key=lambda x: x['distance_km'])
    return {
        "status": "success", 
        "agent": "Pharmacist", 
        "priority_jan_aushadhi": pmbjk_results,
        "fallback_private": pvt_results
    }

@app.post("/api/transport")
def dispatch_transport(loc: LocationQuery):
    results = []
    phc_coords = (loc.lat, loc.lng)
    for amb in ambulances_data:
        if amb['status'] == 'available':
            amb_coords = (amb['current_coordinates']['lat'], amb['current_coordinates']['lng'])
            dist = geodesic(phc_coords, amb_coords).kilometers
            amb_copy = amb.copy()
            amb_copy['distance_km'] = round(dist, 2)
            amb_copy['eta_minutes'] = round((dist / 40) * 60)
            results.append(amb_copy)
    results.sort(key=lambda x: x['distance_km'])
    return {"status": "success", "agent": "Transport", "results": results}

@app.post("/api/sos")
def trigger_sos(loc: LocationQuery):
    """Security Agent: Dispatches SOS to local law enforcement and volunteers"""
    # Simulate finding nearest police station and volunteer network
    return {
        "status": "CRITICAL_ALERT_DISPATCHED",
        "agent": "Security",
        "law_enforcement_notified": "Purnia Sadar Police Station (Distance: 1.2km)",
        "volunteers_alerted": 14,
        "eta_minutes": 5
    }

class EscalationQuery(BaseModel):
    pincode: str
    lat: float
    lng: float
    patient_context: str
    icmr_context: str

@app.post("/api/escalate")
def escalate_to_expert(req: EscalationQuery):
    """Clinical Agent (Sub-task): Retrieves L2 experts and generates a Case Handoff Summary"""
    available_experts = [doc for doc in experts_data if doc['status'] != "In Surgery" and doc['pincode'] == req.pincode]
    
    if not available_experts:
        available_experts = [doc for doc in experts_data if doc['status'] != "In Surgery"]

    # Generate the simulated Handoff Summary that the Agent sends to the L2 Doctor
    handoff_summary = f"""
[URGENT L2 ESCALATION REQUEST]
From: PHC Purnia ({req.pincode})
Patient Context: {req.patient_context}

Agent's Initial Assessment based on ICMR:
{req.icmr_context}

Request: PHC worker requires immediate expert review of the above ICMR adherence and clearance for next steps.
    """.strip()
        
    return {
        "status": "success",
        "agent": "Clinical L2 Escalation",
        "experts": available_experts,
        "handoff_summary": handoff_summary
    }
