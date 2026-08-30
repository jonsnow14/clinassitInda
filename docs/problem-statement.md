

idea is to build  an intelligent assistant  for frontiline PHC worker 

problem statemetn scenarios : 

Scenario : PHC worker needs expert guidance on a patient conditons
 

it is 9 AM at a Primary Health Centre in rural Maharashtra.
A medical officer is alone. Forty patients are waiting outside.
A 45-year-old man walks in  breathless, sweating, BP 160/100.
The nearest district hospital with a cardiologist is 60 kilometres away.

The PHC worker  types into ClinAssist-India:
  Patient 45M, SOB 3 din se, BP 160/100, sugar bhi hai,
     troponin slightly elevated. Kya karna chahiye?

 clinassitindia cinical agent steps in  :
ClinAssistIndia clinical agent   •  v1.0  •  Powered by ICMR  + MIMIC-IV RAG (only ICMR data for phase I)


 URGENT  Yeh case NSTEMI (heart attack) ho sakta hai.
    Abhi refer karein. Neeche diye steps follow karein.

ASSESSMENT
Is patient ki picture serious hai:

  45 saal ka mard + 3 din se saans phoolna (SOB)
  BP high hai: 160/100 → hypertension uncontrolled
  Sugar hai → diabetes → cardiac risk bahut zyada
  Troponin elevated → heart muscle ko injury ho rahi hai

Sabse likely diagnosis:
    NSTEMI (Non-ST Elevation Myocardial Infarction)
    ICD-10: I21.4

ABHI KYA KAREIN  (PHC pe jo ho sakta hai)

Step 1  ECG karo ABHI
  12-lead ECG lagao. ST changes, T-wave inversion dekho.
  Agar STEMI dikh raha hai  even more urgent.

Step 2  Aspirin do ABHI (agar allergy nahi hai)
  Aspirin 325mg  chaba ke khao (swallow nahi, chew karein)
  Yeh clot ko badne se rokta hai.

Step 3  Clopidogrel do
  Clopidogrel 300mg loading dose (4 tablets of 75mg)
  Dual antiplatelet therapy shuru karo.

Step 4  IV access lo
  Saline lock lagao. Fluid nahi dena abhi 
  BP already high hai, fluid se heart pe load aur badh sakta hai.

Step 5  Oxygen
  SpO2 check karo. Agar < 94% hai toh oxygen 4L/min nasal prongs se.
  Agar SpO2 > 94% hai toh oxygen routine nahi dena  ICMR guideline.

Step 6  BP ka kya karein?
  Abhi BP ke liye alag dawai mat do.
  Nitroglycerin sublingual de sakte ho agar chest pain hai
  aur SBP > 100 hai  yahan 160/100 hai toh safe hai.
  Metoprolol ya aur kuch cardiac monitoring ke bina mat do.

Step 7  Kya NAHI dena
   NSAIDs mat do (Diclofenac, Ibuprofen)  troponin aur badhega
   Metformin abhi band karo  contrast dena padega hospital mein
   Insulin adjust mat karo abhi  sugar stress se high hogi

REFER KAREIN TURANT
Nearest District Hospital ya CHC with cardiac unit.
Ambulance call karo  patient khud drive na kare.

Referral slip mein likho:
  "45M, NSTEMI suspected. Troponin elevated.
   Aspirin 325mg + Clopidogrel 300mg given at PHC.
   ECG attached. BP 160/100. Known DM2."

Golden hour: pehle 90 minute mein hospital pahunchna zaroori hai.

FHIR RECORD  ABDM
{
  "resourceType": "Encounter",
  "status": "in-progress",
  "subject": { "display": "45M" },
  "diagnosis": [{
    "condition": { "display": "NSTEMI suspected" },
    "use": { "coding": [{ "code": "I21.4" }]}
  }],
  "medicationRequest": [
    { "medication": "Aspirin 325mg",    "dosage": "stat, chewable"  },
    { "medication": "Clopidogrel 300mg","dosage": "loading dose"    }
  ],
  "referral": {
    "urgency": "URGENT",
    "destination": "District Hospital  Cardiology"
  }
}

SOURCES USED

[1] ICMR Acute Coronary Syndrome Management Guidelines 2022
    Dual antiplatelet therapy, oxygen threshold, STEMI vs NSTEMI  
[2] MIMIC-IV Discharge Note #48291
      Similar: 47M, DM2, HTN, troponin 0.08, Dx NSTEMI
[3] Indian Heart Journal 2021  ACS in South Asian patients
     Earlier onset, higher DM comorbidity, different risk profile

Latency: 2.4s  |  Tokens: 312  |  Cost: ₹0.003
Source mix: 60% ICMR [T1] · 25% MIMIC [T2] · 15% India PubMed [T2]
  ClinAssist output is decision support only.
    Final clinical judgment rests with the treating clinician.

scenario 1.1: the worker is not satisfied with this reponse and needs expert human opinion
 Task 2 for clinassitIndia clinical assitant agent:
 1. agent retrieves  health experts data in the vicinity , rchecks avaialbilty (physical , oncall)
 2. connects the L2 healthcare expert with the pHC worker for expert opinion of agent advise based on ICMR data 

scenario 2:
the PHC worker needs to find available bed in the  primary/secondary/tertriary care hospital nearby
clinassiIndia  operation agent steps in 
 task for clinassitIndia operation agents :
 Task 1
 1. maintains a vector DB of hospitals (goverment and private) nearby with available vacancey (need to brainstorm if maintaining DB should be  a task for Agent or it should be conventially maintained)
 2.when triggered , gets hopsital admission requirements from PHC worker (patient care , exact admission requirement), searches from database and retrieves  best available options
 3. informs the PHC worker about the option
 4. if permitted by the PHC worker, contacts particular operation emergency care and informs about the patients ,shares patient conditions

Task 2:
1. maintains transportation vector DB with  location, availalibitly of all ambulances goverement and public and also volunteers with privater vechiles
2. if prompted by the PHC workere , contacts the transprotation( ambulances-public and private, volunteer transportation) and directs it to location to pick the patinet
3. gives real time movement of ambulance to  PHC worker just like swiggy delivery guy status


scebario  3: 
the PHC worker  is sort of medicines in her stock , needs to find if the medicines are avaialble
 clinassitIndia pharmacist agent steps in 
 Task 1:
 1.  keeps updated list of pharmacist and volunteers in the vicinity with thier active contact numbers
 2. if prompted, contacts the pharmacist with autoamted whatsapp or text message , enquiring the availability of medicine
 3. if receives a matchs , informs human volunteer to collect the medicine from  Pharmacy ,sends routes and location of the pharmacy
 4. tracks the human volunteer movement  like uber and sends real time updates to the PHC worker

  Scenario $ :
  the PHC worker needs help from local law enforcement or community help (from volunteers)
  clinassit India security agent steps in :
  Task :
  1. Maintains database of law enforcement infrasturcre  and community volunteers in the vicinity
  2. if prompted by PHC worker, sends automated SOS for help
  3. Tracks respone and keep PHC worker updated  real time




README structure

- Table of content
- Project Description
- How to reproduce
- Architecture  ( description,diagramitcal representation, include line to architecure.md files)
- What problem it solves
- Some test prompts 
- Existing  constrains
- future roadmap 