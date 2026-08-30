"use client";

import React, { useState } from 'react';
import { Stethoscope, Activity, Truck, Pill, AlertTriangle, Send, Phone, MapPin } from 'lucide-react';

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<any[]>([
    { role: 'system', content: 'ClinAssistIndia Clinical Agent v1.0 • Powered by ICMR Guidelines. Namaste, I am ready to assist. Type a patient symptom or use the Quick Actions.' }
  ]);
  const [loading, setLoading] = useState(false);
  const [activePanel, setActivePanel] = useState<'chat' | 'ops' | 'pharmacy' | 'sos'>('chat');
  
  const [opsData, setOpsData] = useState<any>(null);
  const [pharmacyData, setPharmacyData] = useState<any>(null);
  const [sosData, setSosData] = useState<any>(null);

  // Real-time tracking simulation state
  const [liveAmbulances, setLiveAmbulances] = useState<any[]>([]);

  // Mock PHC Location (Purnia, Bihar)
  const phcLocation = { pincode: "854301", lat: 25.7770, lng: 87.4750 };

  const handleClinicalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMsg = query;
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setQuery('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/clinical', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'agent', content: data }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'system', content: 'Error connecting to Clinical Agent.' }]);
    }
    setLoading(false);
  };

  const triggerOpsAgent = async () => {
    setLoading(true);
    setActivePanel('ops');
    try {
      const resBeds = await fetch('http://127.0.0.1:8000/api/beds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(phcLocation)
      });
      const dataBeds = await resBeds.json();

      const resAmb = await fetch('http://127.0.0.1:8000/api/transport', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(phcLocation)
      });
      const dataAmb = await resAmb.json();
      
      setOpsData({ beds: dataBeds.results, ambulances: dataAmb.results });
      
      // Initialize Real-Time Tracking State
      setLiveAmbulances(dataAmb.results.map((a: any) => ({ ...a, status: 'dispatched' })));
      
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  // Real-Time Polling Effect for Ambulances
  React.useEffect(() => {
    if (activePanel !== 'ops' || liveAmbulances.length === 0) return;
    
    const interval = setInterval(() => {
      setLiveAmbulances(prev => 
        prev.map(amb => {
          // Simulate movement by decreasing ETA and distance every tick
          const newEta = Math.max(0, amb.eta_minutes - 1);
          const newDist = Math.max(0, (amb.distance_km - 0.5).toFixed(1));
          return { ...amb, eta_minutes: newEta, distance_km: newDist };
        })
      );
    }, 3000); // Ticks every 3 seconds for the demo

    return () => clearInterval(interval);
  }, [activePanel, liveAmbulances.length]);

  const triggerPharmacyAgent = async () => {
    setLoading(true);
    setActivePanel('pharmacy');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/pharmacy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(phcLocation)
      });
      const data = await res.json();
      setPharmacyData(data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const triggerEscalationAgent = async (messageIndex: number) => {
    try {
      const msgContext = messages[messageIndex];
      const reqBody = {
        ...phcLocation,
        patient_context: msgContext.content.sarvam_translation || "Patient data",
        icmr_context: msgContext.content.icmr_rule_retrieved || "ICMR Rule"
      };

      const res = await fetch('http://127.0.0.1:8000/api/escalate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      const data = await res.json();
      
      // Attach the escalation data to the specific chat message
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[messageIndex] = { ...newMsgs[messageIndex], escalationData: data };
        return newMsgs;
      });
    } catch (err) {
      console.error("Escalation failed", err);
    }
  };

  const triggerSosAgent = async () => {
    setLoading(true);
    setActivePanel('sos');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(phcLocation)
      });
      const data = await res.json();
      setSosData(data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      
      {/* Sidebar Navigation */}
      <div className="w-20 bg-blue-900 flex flex-col items-center py-6 gap-8 shadow-xl z-20">
        <div className="bg-white p-2 rounded-xl text-blue-900 shadow-sm cursor-pointer" onClick={() => setActivePanel('chat')} title="Clinical Assistant">
          <Stethoscope size={28} />
        </div>
        <div className="text-blue-100 hover:text-white cursor-pointer transition-colors" onClick={triggerOpsAgent} title="Operations (Beds & Transport)">
          <Activity size={28} />
        </div>
        <div className="text-blue-100 hover:text-white cursor-pointer transition-colors" onClick={triggerPharmacyAgent} title="Pharmacy (Jan Aushadhi)">
          <Pill size={28} />
        </div>
        <div className="mt-auto text-red-400 hover:text-red-500 cursor-pointer transition-colors bg-red-50 hover:bg-red-100 p-2 rounded-xl" onClick={triggerSosAgent} title="Emergency SOS">
          <AlertTriangle size={28} />
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex justify-between items-center shadow-sm z-10">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">ClinAssistIndia</h1>
            <p className="text-sm text-slate-500">Primary Health Centre - Purnia, Bihar (PIN: 854301)</p>
          </div>
          <div className="flex gap-4">
             <button onClick={triggerOpsAgent} className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-slate-200">
               <Truck size={16} /> Find Ambulance
             </button>
             <button onClick={triggerPharmacyAgent} className="flex items-center gap-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-emerald-200">
               <Pill size={16} /> Check Jan Aushadhi
             </button>
             <button onClick={triggerSosAgent} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-bold transition-colors shadow-sm">
               <AlertTriangle size={16} /> Trigger SOS
             </button>
          </div>
        </header>

        {/* Dynamic Panels */}
        <main className="flex-1 overflow-auto p-6 flex flex-col items-center bg-slate-50">
          
          {activePanel === 'chat' && (
            <div className="w-full max-w-4xl bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[calc(100vh-8rem)]">
              {/* Chat History */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800 border border-slate-200'}`}>
                      {msg.role === 'system' ? (
                         <div className="flex items-center gap-2 text-slate-500 text-sm font-medium">
                           <Stethoscope size={16} /> {msg.content}
                         </div>
                      ) : msg.role === 'user' ? (
                         <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <div className="space-y-4">
                           {/* Clinical Agent Response Formatter */}
                           <div className="flex items-center gap-2 text-blue-700 font-bold border-b border-slate-200 pb-2 mb-3">
                              <Activity size={18} /> Diagnosis & Action Plan
                           </div>
                           
                           {/* Simulating Sarvam's extracted intent quietly */}
                           <p className="text-xs text-slate-400 font-mono bg-slate-200 p-2 rounded">
                             Intent Extracted: {msg.content.sarvam_translation}
                           </p>

                           {/* ICMR Rule */}
                           <div className="bg-white p-3 rounded-lg border border-slate-200 text-sm">
                             <h4 className="font-bold text-slate-700 mb-1">ICMR Grounding:</h4>
                             <p className="text-slate-600 whitespace-pre-wrap">{msg.content.icmr_rule_retrieved}</p>
                           </div>

                           <div className="flex gap-4 mt-4">
                             <div className="flex-1 bg-blue-50 border border-blue-200 p-4 rounded-xl">
                               <h4 className="font-bold text-blue-900 mb-2 flex items-center gap-2">DO IMMEDIATELY:</h4>
                               <ul className="list-disc pl-5 text-sm text-blue-800 space-y-1">
                                  {msg.content.recommended_actions.map((act: string, i: number) => <li key={i}>{act}</li>)}
                               </ul>
                             </div>
                             <div className="flex-1 bg-red-50 border border-red-200 p-4 rounded-xl">
                               <h4 className="font-bold text-red-900 mb-2 flex items-center gap-2">DO NOT DO:</h4>
                               <ul className="list-disc pl-5 text-sm text-red-800 space-y-1">
                                  {msg.content.do_not_do.map((act: string, i: number) => <li key={i}>{act}</li>)}
                               </ul>
                             </div>
                           </div>

                           {/* Escalate to L2 Expert */}
                           <div className="mt-4 border-t border-slate-200 pt-3">
                             <button 
                               onClick={() => triggerEscalationAgent(idx)}
                               className="text-sm bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
                             >
                               <Phone size={14} /> Need L2 Expert Opinion? Escalate
                             </button>
                             
                             {msg.escalationData && (
                               <div className="mt-3 p-4 bg-indigo-50 border border-indigo-200 rounded-xl">
                                  <h4 className="font-bold text-indigo-900 mb-2">L2 Handoff Generated:</h4>
                                  
                                  {/* The Output the Agent generated for the L2 Doctor */}
                                  <div className="bg-slate-800 text-green-400 font-mono text-xs p-3 rounded-lg mb-4 whitespace-pre-wrap">
                                     {msg.escalationData.handoff_summary}
                                  </div>

                                  <h4 className="font-bold text-indigo-900 mb-2">Connecting to Available Specialists:</h4>
                                  <div className="space-y-2">
                                     {msg.escalationData.experts.map((doc: any) => (
                                        <div key={doc.id} className="flex justify-between items-center bg-white p-3 rounded-lg border border-indigo-100 shadow-sm">
                                           <div>
                                              <p className="font-bold text-slate-800">{doc.name}</p>
                                              <p className="text-xs text-slate-500">{doc.specialty} • {doc.hospital}</p>
                                           </div>
                                           <div className="flex flex-col items-end">
                                              <span className="text-xs font-bold text-emerald-600 bg-emerald-100 px-2 py-1 rounded mb-1">{doc.status}</span>
                                              <button className="text-sm bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700 transition">Establish Secure Tele-Consult</button>
                                           </div>
                                        </div>
                                     ))}
                                  </div>
                               </div>
                             )}
                           </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {loading && (
                   <div className="flex justify-start">
                      <div className="bg-slate-100 text-slate-500 border border-slate-200 p-4 rounded-2xl flex items-center gap-3">
                         <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                         Agent is thinking...
                      </div>
                   </div>
                )}
              </div>

              {/* Chat Input */}
              <div className="p-4 bg-slate-50 border-t border-slate-200 rounded-b-2xl">
                <form onSubmit={handleClinicalSubmit} className="flex gap-3 relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Type patient symptoms (e.g. '45M, SOB 3 din se, BP 160/100...')"
                    className="flex-1 px-6 py-4 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm text-slate-800 bg-white"
                  />
                  <button type="submit" disabled={loading} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-xl font-medium transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center">
                    <Send size={20} />
                  </button>
                </form>
              </div>
            </div>
          )}

          {activePanel === 'ops' && opsData && (
             <div className="w-full max-w-5xl space-y-6 animate-in fade-in slide-in-from-bottom-4">
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                  <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2"><Activity /> Operations Agent: Nearby Beds</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {opsData.beds.map((b: any) => (
                       <div key={b.id} className="border border-slate-200 rounded-xl p-4 bg-slate-50">
                          <div className="flex justify-between items-start mb-2">
                             <h3 className="font-bold text-slate-800">{b.name}</h3>
                             <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-bold">{b.distance_km} km away</span>
                          </div>
                          <p className="text-sm text-slate-500 mb-3">{b.type}</p>
                          <div className="flex gap-4 text-sm font-medium">
                             <div className="bg-red-50 text-red-700 px-3 py-1 rounded-lg">ICU: {b.beds.icu_available}</div>
                             <div className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg">Oxygen: {b.beds.oxygen_available}</div>
                          </div>
                       </div>
                     ))}
                  </div>
                </div>

                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                  <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <Truck /> Transport Agent: Live Ambulance Tracking
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {liveAmbulances.map((a: any) => (
                       <div key={a.id} className="border border-blue-200 rounded-xl p-4 bg-blue-50 relative overflow-hidden">
                          {/* Simulated moving progress bar underneath */}
                          <div 
                             className="absolute bottom-0 left-0 h-1 bg-blue-600 transition-all duration-1000" 
                             style={{ width: `${Math.min(100, (20 - a.eta_minutes) * 5)}%` }} 
                          />
                          <div className="flex justify-between items-start mb-2">
                             <h3 className="font-bold text-blue-900">{a.provider}</h3>
                             <span className="bg-blue-600 text-white animate-pulse text-xs px-2 py-1 rounded-full font-bold">
                               ETA: {a.eta_minutes > 0 ? `${a.eta_minutes} mins` : "ARRIVED"}
                             </span>
                          </div>
                          <p className="text-sm text-blue-700 mb-3">{a.type} • {a.distance_km} km away</p>
                          <button disabled className="w-full bg-slate-300 text-slate-600 font-bold py-2 rounded-lg cursor-not-allowed">
                            Dispatched & Tracking...
                          </button>
                       </div>
                     ))}
                  </div>
                </div>
             </div>
          )}

          {activePanel === 'pharmacy' && pharmacyData && (
             <div className="w-full max-w-5xl space-y-6 animate-in fade-in slide-in-from-bottom-4">
                
                <div className="bg-emerald-50 p-6 rounded-2xl border border-emerald-200">
                  <h2 className="text-xl font-bold text-emerald-900 mb-2 flex items-center gap-2"><Pill /> Pharmacist Agent: Jan Aushadhi First</h2>
                  <p className="text-emerald-700 text-sm mb-6">Strict routing rule applied: PMBJK centers prioritized for rural affordability.</p>
                  
                  <h3 className="font-bold text-emerald-800 mb-3">Priority: Pradhan Mantri Bhartiya Janaushadhi Kendras</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                     {pharmacyData.priority_jan_aushadhi.map((p: any) => (
                       <div key={p.id} className="bg-white rounded-xl p-4 border border-emerald-300 shadow-sm">
                          <div className="flex justify-between items-start mb-2">
                             <h3 className="font-bold text-emerald-900">{p.name}</h3>
                             <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-1 rounded-full font-bold">{p.distance_km} km away</span>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-emerald-700 mb-3 font-medium">
                             <Phone size={14} /> {p.contact}
                          </div>
                          <div className="flex justify-between items-center">
                             <span className="text-xs font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded">Stock: {p.stock_status}</span>
                             <button className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors">
                               Contact
                             </button>
                          </div>
                       </div>
                     ))}
                  </div>

                  <h3 className="font-bold text-slate-500 mb-3">Fallback: Private Pharmacies</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                     {pharmacyData.fallback_private.map((p: any) => (
                       <div key={p.id} className="bg-white rounded-xl p-4 border border-slate-200 opacity-75">
                          <div className="flex justify-between items-start mb-2">
                             <h3 className="font-bold text-slate-700">{p.name}</h3>
                             <span className="bg-slate-100 text-slate-600 text-xs px-2 py-1 rounded-full font-bold">{p.distance_km} km away</span>
                          </div>
                          <p className="text-xs text-slate-500 mb-2">{p.type} Provider</p>
                       </div>
                     ))}
                  </div>
                </div>

             </div>
          )}

          {activePanel === 'sos' && sosData && (
             <div className="w-full max-w-5xl space-y-6 animate-in fade-in slide-in-from-bottom-4">
                <div className="bg-red-50 border-2 border-red-500 p-8 rounded-2xl text-center shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-red-600 animate-pulse"></div>
                  
                  <AlertTriangle size={64} className="mx-auto text-red-600 mb-4 animate-bounce" />
                  <h2 className="text-3xl font-black text-red-800 mb-2 uppercase tracking-wide">
                    {sosData.status.replace(/_/g, " ")}
                  </h2>
                  <p className="text-red-700 text-lg mb-8">
                    Emergency protocols have been activated for PIN {phcLocation.pincode}.
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
                     <div className="bg-white p-5 rounded-xl border border-red-200 shadow-sm">
                        <h3 className="font-bold text-slate-800 mb-2">Law Enforcement</h3>
                        <p className="text-emerald-600 font-bold flex items-center gap-2">
                           ✓ Notified: {sosData.law_enforcement_notified}
                        </p>
                     </div>
                     <div className="bg-white p-5 rounded-xl border border-red-200 shadow-sm">
                        <h3 className="font-bold text-slate-800 mb-2">Community Volunteers</h3>
                        <p className="text-emerald-600 font-bold flex items-center gap-2">
                           ✓ Alerted: {sosData.volunteers_alerted} personnel
                        </p>
                     </div>
                  </div>
                </div>
             </div>
          )}

        </main>
      </div>
    </div>
  );
}
