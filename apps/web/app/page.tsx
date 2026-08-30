"use client";

import dynamic from "next/dynamic";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BedsCard,
  ClinicalCardView,
  ExpertCard,
  PharmacyCard,
  SosCard,
  TransportCard,
} from "@/components/Cards";
import { api } from "@/lib/api";
import type {
  AgentId,
  ClinicalCard,
  Expert,
  Health,
  Hospital,
  Message,
  Pharmacy,
  SuggestedAction,
  Track,
} from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const GOLDEN =
  "Patient 45M, SOB 3 din se, BP 160/100, sugar bhi hai, troponin slightly elevated. Kya karna chahiye?";

const AGENTS: { id: AgentId; label: string }[] = [
  { id: "clinical", label: "क्लिनिकल" },
  { id: "beds", label: "बेड" },
  { id: "transport", label: "एम्बुलेंस" },
  { id: "pharmacy", label: "दवाई" },
  { id: "expert", label: "एक्सपर्ट" },
  { id: "sos", label: "SOS" },
];

/**
 * Generates a unique pseudo-random ID string for chat messages.
 *
 * @returns {string} Short unique ID.
 */
function uid() {
  return Math.random().toString(36).slice(2);
}

/**
 * Main application dashboard for ClinAssistIndia PHC workers.
 * Features clinical decision workspace, real-time script transliteration (Mayura),
 * specialized sub-agents (Beds, Transport, Pharmacy, Expert, SOS), and dynamic map view.
 */
export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState(false);
  const [intent, setIntent] = useState<AgentId>("clinical");
  const [text, setText] = useState("");
  const [scriptHint, setScriptHint] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [track, setTrack] = useState<Track | null>(null);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [sheet, setSheet] = useState(false);
  const [sosOpen, setSosOpen] = useState(false);
  const [lastCard, setLastCard] = useState<ClinicalCard | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const pendingRoman = useRef("");
  const translatingRef = useRef(false);

  const hasLatin = (s: string) => /[A-Za-z]{2,}/.test(s);

  const runMayura = useCallback(async (snapshot: string) => {
    if (!snapshot.trim() || snapshot.trim().startsWith("/")) return snapshot;
    if (!hasLatin(snapshot)) return snapshot;
    translatingRef.current = true;
    setScriptHint("Mayura: रोमन → देवनागरी…");
    try {
      const res = await api.toHindi(snapshot);
      const next = res.text || snapshot;
      if (pendingRoman.current === snapshot) {
        setText(next);
        setScriptHint(hasLatin(next) ? "कुछ रोमन बचा — Enter फिर दबाएँ" : "देवनागरी (mayura:v1)");
      }
      return next;
    } catch {
      setScriptHint("");
      return snapshot;
    } finally {
      translatingRef.current = false;
    }
  }, []);
  const debug =
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("debug") === "1";

  const refreshHealth = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setHealthErr(false);
    } catch {
      setHealthErr(true);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    const t = setInterval(refreshHealth, 15000);
    return () => clearInterval(t);
  }, [refreshHealth]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    const raw = text.trim();
    if (raw.length < 2 || raw.startsWith("/") || !hasLatin(text)) {
      if (!hasLatin(text)) setScriptHint((h) => (h.startsWith("Mayura") ? "" : h));
      return;
    }
    pendingRoman.current = text;
    const t = setTimeout(() => {
      void runMayura(pendingRoman.current);
    }, 400);
    return () => clearTimeout(t);
  }, [text, runMayura]);

  useEffect(() => {
    if (!track || track.status === "arrived") return;
    const path = track.kind === "courier" ? api.courierTrack : api.transportTrack;
    const t = setInterval(async () => {
      try {
        const next = await path(track.trip_id);
        setTrack(next);
        setMessages((ms) =>
          ms.map((m) =>
            m.role === "agent" && (m.kind === "transport" || m.kind === "courier") && m.track.trip_id === next.trip_id
              ? { ...m, track: next }
              : m,
          ),
        );
      } catch {
        /* ignore poll errors */
      }
    }, 3000);
    return () => clearInterval(t);
  }, [track]);

  const caseReady = Boolean(lastCard);

  const phc = health?.phc || { lat: 25.7771, lng: 87.4753, name: "PHC Purnia", pincode: "854301", district: "Purnia", state: "Bihar", id: "phc-purnia" };

  const statusPill = useMemo(() => {
    if (healthErr) return { text: "Backend offline", cls: "bg-urgent" };
    if (!health) return { text: "Connecting", cls: "bg-warn text-black" };
    if (!health.sarvam_key_present) return { text: "Need SARVAM_API_KEY", cls: "bg-urgent" };
    if (!health.chroma_ready) return { text: "ICMR index empty", cls: "bg-warn text-black" };
    return { text: "LIVE", cls: "bg-safe" };
  }, [health, healthErr]);

  function push(...items: Message[]) {
    setMessages((m) => [...m, ...items]);
  }

  async function runClinical(prompt: string) {
    setBusy(true);
    try {
      const card = await api.consult(prompt);
      setLastCard(card);
      push({ id: uid(), role: "agent", kind: "clinical", card });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  async function runBeds() {
    setBusy(true);
    try {
      const res = await api.beds("icu");
      setHospitals(res.hospitals);
      setSheet(true);
      push({
        id: uid(),
        role: "agent",
        kind: "beds",
        hospitals: res.hospitals,
        need: res.need,
        note: res.note,
      });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  async function runTransport() {
    setBusy(true);
    try {
      const t = await api.transportDispatch();
      setTrack(t);
      setSheet(true);
      push({ id: uid(), role: "agent", kind: "transport", track: t });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  async function runPharmacy() {
    setBusy(true);
    try {
      const res = await api.pharmacy();
      setSheet(true);
      push({
        id: uid(),
        role: "agent",
        kind: "pharmacy",
        pharmacies: res.pharmacies,
        note: res.note,
      });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  async function runExperts() {
    setBusy(true);
    try {
      const res = await api.experts();
      push({ id: uid(), role: "agent", kind: "expert", experts: res.experts });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  async function confirmSos(reason: "security" | "community") {
    setSosOpen(false);
    setBusy(true);
    try {
      const sos = await api.sos(reason, lastCard?.diagnosis.name || "");
      push({ id: uid(), role: "agent", kind: "sos", sos });
    } catch (err) {
      push({ id: uid(), role: "agent", kind: "error", text: String(err) });
    } finally {
      setBusy(false);
    }
  }

  function handleAction(a: SuggestedAction | AgentId) {
    if (a === "clinical") {
      setIntent("clinical");
      return;
    }
    if (a === "sos") {
      setSosOpen(true);
      return;
    }
    if (a !== "beds" && a !== "transport" && a !== "pharmacy" && a !== "expert") return;
    if (!caseReady) {
      push({
        id: uid(),
        role: "agent",
        kind: "info",
        text: "पहले क्लिनिकल सलाह भेजें — एजेंट तभी चलेंगे जब आप उन्हें दबाएँ।",
      });
    }
    setIntent(a);
    if (a === "beds") void runBeds();
    if (a === "transport") void runTransport();
    if (a === "pharmacy") void runPharmacy();
    if (a === "expert") void runExperts();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    let raw = text.trim();
    if (!raw) return;
    let nextIntent: AgentId = intent;
    const slash = raw.match(/^\/(clinical|beds|transport|pharmacy|expert|sos)\b/i);
    if (slash) {
      nextIntent = slash[1].toLowerCase() as AgentId;
      raw = raw.slice(slash[0].length).trim();
      setIntent(nextIntent);
    }
    if (raw) {
      raw = await runMayura(raw);
      push({ id: uid(), role: "worker", text: raw });
    }
    setText("");
    setScriptHint("");
    if (nextIntent === "clinical") {
      if (!raw) return;
      await runClinical(raw);
      return;
    }
    handleAction(nextIntent);
  }

  const agentDisabled = (id: AgentId) => {
    if (id === "clinical" || id === "sos") return false;
    return !caseReady;
  };

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-4 py-3">
        <div>
          <div className="text-sm font-bold tracking-wide text-muted">CLINASSISTINDIA v1.0</div>
          <div className="text-lg font-bold">
            {phc.name} · PIN {phc.pincode}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-bold ${statusPill.cls}`}>{statusPill.text}</span>
          <button className="btn-sos" type="button" onClick={() => setSosOpen(true)}>
            SOS
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <nav className="flex gap-2 overflow-x-auto border-b border-line p-3 md:w-44 md:flex-col md:border-b-0 md:border-r">
          {AGENTS.map((a) => (
            <button
              key={a.id}
              type="button"
              disabled={agentDisabled(a.id)}
              onClick={() => handleAction(a.id)}
              className={`chip whitespace-nowrap ${intent === a.id ? "chip-active" : ""} ${a.id === "sos" ? "text-urgent" : ""}`}
            >
              {a.label}
            </button>
          ))}
        </nav>

        <main className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div ref={threadRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="card text-muted">
                <p className="font-semibold text-ink">PHC case workspace</p>
                <p className="mt-2 text-[16px]">
                  Hinglish mein patient likhein. Clinical agent ICMR STW se retrieve karke Sarvam se jawab dega.
                  Dusre agents (beds, ambulance, pharmacy, expert, SOS) tabhi chalenge jab aap unhe tap karein.
                </p>
                <button
                  type="button"
                  className="btn-secondary mt-3"
                  onClick={() => {
                    setText(GOLDEN);
                    setIntent("clinical");
                  }}
                >
                  Load NSTEMI prompt
                </button>
              </div>
            )}
            {messages.map((m) => {
              if (m.role === "worker") {
                return (
                  <div key={m.id} className="ml-auto max-w-[92%] rounded-2xl bg-[#1d4ed8] px-4 py-3">
                    {m.text}
                  </div>
                );
              }
              if (m.kind === "clinical")
                return (
                  <ClinicalCardView
                    key={m.id}
                    card={m.card}
                    debug={debug}
                    onAction={(a) => handleAction(a)}
                  />
                );
              if (m.kind === "beds")
                return (
                  <BedsCard
                    key={m.id}
                    hospitals={m.hospitals}
                    note={m.note}
                    onRefer={(h) =>
                      push({
                        id: uid(),
                        role: "agent",
                        kind: "info",
                        text: `Referral noted: ${h.name} (${h.km} km). Slip: ${lastCard?.referral.slip || h.name}`,
                      })
                    }
                  />
                );
              if (m.kind === "transport" || m.kind === "courier")
                return <TransportCard key={m.id} track={m.track} />;
              if (m.kind === "pharmacy")
                return (
                  <PharmacyCard
                    key={m.id}
                    pharmacies={m.pharmacies}
                    note={m.note}
                    onDispatch={async (p: Pharmacy) => {
                      try {
                        const t = await api.pharmacyDispatch(p.id, p.wanted);
                        setTrack(t);
                        setSheet(true);
                        push({ id: uid(), role: "agent", kind: "courier", track: t });
                      } catch (err) {
                        push({ id: uid(), role: "agent", kind: "error", text: String(err) });
                      }
                    }}
                  />
                );
              if (m.kind === "expert" && m.experts)
                return (
                  <ExpertCard
                    key={m.id}
                    experts={m.experts}
                    onConnect={async (e: Expert) => {
                      try {
                        const c = await api.expertConsult(e.id, lastCard?.diagnosis.name || "");
                        push({
                          id: uid(),
                          role: "agent",
                          kind: "info",
                          text: `${c.status}: ${c.expert.name} (${c.expert.specialty}). ${c.note}`,
                        });
                      } catch (err) {
                        push({ id: uid(), role: "agent", kind: "error", text: String(err) });
                      }
                    }}
                  />
                );
              if (m.kind === "sos") return <SosCard key={m.id} sos={m.sos} />;
              if (m.kind === "error")
                return (
                  <div key={m.id} className="card border-urgent/40 text-urgent">
                    {m.text}
                  </div>
                );
              return (
                <div key={m.id} className="card text-muted">
                  {m.kind === "info" ? m.text : null}
                </div>
              );
            })}
            {busy && (
              <div className="text-sm text-muted">
                एजेंट काम कर रहा है… सरवम + ICMR लगभग ३०–६० सेकंड। पेज न बंद करें।
              </div>
            )}
          </div>

          <form onSubmit={onSubmit} className="border-t border-line bg-panel p-3">
            <div className="flex gap-2">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key !== "Enter" || e.shiftKey) return;
                  e.preventDefault();
                  if (hasLatin(text)) {
                    pendingRoman.current = text;
                    void runMayura(text);
                    return;
                  }
                  (e.currentTarget.form as HTMLFormElement | null)?.requestSubmit();
                }}
                placeholder="रोमन में टाइप करें — हिंदी देवनागरी दिखेगी (Enter = बदलें / भेजें, Shift+Enter = नई पंक्ति)"
                rows={2}
                className="min-h-[48px] flex-1 resize-none rounded-xl border border-line bg-card px-3 py-3 outline-none"
                lang="hi"
              />
              <button className="btn-primary" type="submit" disabled={busy}>
                भेजें
              </button>
            </div>
            {scriptHint ? <p className="mt-1 text-xs text-muted">{scriptHint}</p> : null}
          </form>
        </main>

        <aside
          className={`${sheet ? "fixed inset-x-0 bottom-0 z-20 h-[45vh] md:static md:h-auto" : "hidden md:flex"} w-full flex-col border-t border-line bg-panel p-3 md:w-[360px] md:border-l md:border-t-0`}
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="label">MAP / CONTEXT</span>
            <button className="text-sm text-muted md:hidden" type="button" onClick={() => setSheet(false)}>
              Close
            </button>
          </div>
          <div className="min-h-[240px] flex-1">
            <MapView phc={phc} hospitals={hospitals} track={track} />
          </div>
          <button className="chip mt-2 md:hidden" type="button" onClick={() => setSheet(true)}>
            Open map
          </button>
        </aside>
      </div>

      <button
        type="button"
        className="fixed bottom-24 right-4 z-10 rounded-full bg-panel px-4 py-3 text-sm shadow md:hidden"
        onClick={() => setSheet(true)}
      >
        Map
      </button>

      {sosOpen && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/70 p-4 md:items-center">
          <div className="card w-full max-w-md space-y-3">
            <h2 className="text-xl font-bold">Alert thana + volunteers?</h2>
            <p className="text-muted">
              POC simulated SOS — no real SMS. Confirm to notify local contacts.
            </p>
            <div className="flex flex-col gap-2">
              <button className="btn-sos w-full" type="button" onClick={() => confirmSos("security")}>
                Law enforcement
              </button>
              <button className="btn-primary w-full" type="button" onClick={() => confirmSos("community")}>
                Community volunteers
              </button>
              <button className="btn-secondary w-full" type="button" onClick={() => setSosOpen(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
