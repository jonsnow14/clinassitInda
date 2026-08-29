"use client";

import type {
  ClinicalCard,
  Expert,
  Hospital,
  Pharmacy,
  SosStatus,
  SuggestedAction,
  Track,
} from "@/lib/types";

export function UrgentBanner({ urgency, title }: { urgency: string; title: string }) {
  const cls =
    urgency === "urgent"
      ? "bg-urgent"
      : urgency === "priority"
        ? "bg-warn text-black"
        : "bg-safe";
  return (
    <div className={`${cls} rounded-lg px-3 py-2 text-[15px] font-bold uppercase tracking-wide`}>
      {urgency} · {title}
    </div>
  );
}

export function ClinicalCardView({
  card,
  debug,
  onAction,
}: {
  card: ClinicalCard;
  debug?: boolean;
  onAction: (a: SuggestedAction) => void;
}) {
  return (
    <article className="card space-y-3">
      <UrgentBanner urgency={card.urgency} title={card.diagnosis.name} />
      {card.diagnosis.icd10 && (
        <p className="text-sm text-muted">
          ICD-10: <span className="font-mono text-ink">{card.diagnosis.icd10}</span> · confidence{" "}
          {Math.round(card.diagnosis.confidence * 100)}%
        </p>
      )}
      <section>
        <h3 className="label">ASSESSMENT</h3>
        <ul className="mt-1 list-disc space-y-1 pl-5 text-[16px]">
          {card.assessment.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </section>
      <section>
        <h3 className="label">ABHI KYA KAREIN (PHC)</h3>
        {card.steps.length === 0 ? (
          <p className="mt-1 text-[15px] text-muted">
            Passages mile, lekin structured steps nahi. Neeche sources padhein ya Expert tap karein.
          </p>
        ) : (
          <ol className="mt-1 space-y-2">
            {card.steps.map((s) => (
              <li key={s.n} className="flex gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 text-sm font-bold">
                  {s.n}
                </span>
                <div>
                  <div className="font-semibold">{s.title}</div>
                  <div className="text-[15px] text-muted">{s.detail}</div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
      {card.do_nots.length > 0 && (
        <section className="rounded-lg border border-urgent/40 bg-urgent/10 p-3">
          <h3 className="label text-urgent">KYA NAHI DENA</h3>
          <ul className="mt-1 list-disc pl-5 text-[15px]">
            {card.do_nots.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </section>
      )}
      {card.referral.required && (
        <section className="rounded-lg border border-warn/50 bg-warn/10 p-3">
          <h3 className="label text-warn">REFER KAREIN</h3>
          <p className="font-semibold">{card.referral.destination}</p>
          <p className="whitespace-pre-wrap text-[15px] text-muted">{card.referral.slip}</p>
          {card.referral.golden_hour_min ? (
            <p className="mt-1 font-bold text-urgent">
              Golden hour: {card.referral.golden_hour_min} min
            </p>
          ) : null}
        </section>
      )}
      <details className="rounded-lg bg-black/20 p-2">
        <summary className="label cursor-pointer">SOURCES (ICMR RAG) — {card.sources.length} passages</summary>
        <ol className="mt-2 space-y-2 text-[13px] text-muted">
          {card.sources.map((s) => (
            <li key={s.n} className="rounded-md bg-black/30 p-2">
              <span className="font-semibold text-ink">
                [{s.n}] {s.stw_title}
              </span>{" "}
              <span className="text-xs">
                {s.pdf} {s.section}
              </span>
              <p className="mt-1 line-clamp-4">{s.quote}</p>
            </li>
          ))}
        </ol>
      </details>
      <p className="text-xs text-muted">
        {card.disclaimer}
        {debug && card.fhir_id ? ` · FHIR ${card.fhir_id.slice(0, 8)}` : ""} · {card.latency_ms} ms
        {card.model ? ` · ${card.model}` : ""} · {card.retrieval.chunk_count} chunks
      </p>
      <div className="flex flex-wrap gap-2">
        {card.suggested_actions.map((a) => (
          <button key={a} className="chip" onClick={() => onAction(a)} type="button">
            {actionLabel(a)}
          </button>
        ))}
      </div>
    </article>
  );
}

export function actionLabel(a: SuggestedAction) {
  return {
    beds: "बेड खोजें",
    transport: "एम्बुलेंस",
    pharmacy: "दवाई",
    expert: "एक्सपर्ट",
    sos: "SOS",
  }[a];
}

export function BedsCard({
  hospitals,
  note,
  onRefer,
}: {
  hospitals: Hospital[];
  note?: string;
  onRefer: (h: Hospital) => void;
}) {
  if (!hospitals.length) return <p className="card text-muted">No beds in the local directory.</p>;
  return (
    <div className="space-y-2">
      {note ? <p className="text-xs text-muted">{note}</p> : null}
      {hospitals.map((h) => (
        <article key={h.id} className="card">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold">{h.name}</h3>
              <p className="text-sm text-muted">
                {h.type} · {h.km} km · {h.phone}
              </p>
            </div>
            {h.accepts_nstemi && <span className="badge-safe">NSTEMI</span>}
          </div>
          <p className="mt-2 text-sm">
            ICU {h.beds_icu} · O₂ {h.beds_oxygen} · General {h.beds_general}
          </p>
          <p className="text-xs text-muted">{h.notes}</p>
          <button className="btn-secondary mt-2" type="button" onClick={() => onRefer(h)}>
            Refer here
          </button>
        </article>
      ))}
    </div>
  );
}

export function TransportCard({ track }: { track: Track }) {
  return (
    <article className="card">
      <h3 className="font-semibold">{track.vehicle?.name}</h3>
      <p className="text-sm text-muted">
        {track.vehicle?.kind} · {track.vehicle?.phone}
      </p>
      <p className="mt-2 text-lg font-bold">
        {track.status === "arrived" ? "PHC pe pahunch gayi" : `En route · ETA ${track.eta_min} min`}
      </p>
    </article>
  );
}

export function PharmacyCard({
  pharmacies,
  note,
  onDispatch,
}: {
  pharmacies: Pharmacy[];
  note: string;
  onDispatch: (p: Pharmacy) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted">{note}</p>
      {pharmacies.map((p) => (
        <article key={p.id} className="card">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold">{p.name}</h3>
            {p.jan_aushadhi ? (
              <span className="badge-safe">Jan Aushadhi</span>
            ) : (
              <span className="badge-muted">Private</span>
            )}
          </div>
          <p className="text-sm text-muted">
            {p.km} km · {p.phone}
          </p>
          <p className="mt-1 text-sm">
            {p.has_all ? "Wanted meds in stock" : `Missing: ${p.missing.join(", ") || "—"}`}
          </p>
          <button className="btn-secondary mt-2" type="button" onClick={() => onDispatch(p)}>
            Assign volunteer
          </button>
        </article>
      ))}
    </div>
  );
}

export function ExpertCard({
  experts,
  onConnect,
}: {
  experts: Expert[];
  onConnect: (e: Expert) => void;
}) {
  const color = (a: string) =>
    a === "available" ? "bg-safe" : a === "on_call" ? "bg-warn" : "bg-urgent";
  return (
    <div className="space-y-2">
      {experts.map((e) => (
        <article key={e.id} className="card flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className={`inline-block h-3 w-3 rounded-full ${color(e.availability)}`} />
              <h3 className="font-semibold">{e.name}</h3>
            </div>
            <p className="text-sm text-muted">
              {e.specialty} · {e.facility} · {e.availability} · {e.eta_min} min
            </p>
          </div>
          <button
            className="btn-secondary"
            type="button"
            disabled={e.availability === "busy"}
            onClick={() => onConnect(e)}
          >
            Connect
          </button>
        </article>
      ))}
    </div>
  );
}

export function SosCard({ sos }: { sos: SosStatus }) {
  return (
    <article className="card border-urgent/50">
      <UrgentBanner urgency="urgent" title={`SOS ${sos.reason}`} />
      <p className="mt-2 text-sm">
        Status: <strong>{sos.ack}</strong> · ETA {sos.eta_min} min
      </p>
      <ul className="mt-2 text-sm text-muted">
        {sos.contacts_notified.map((c) => (
          <li key={c.id}>
            {c.name} · {c.phone}
          </li>
        ))}
      </ul>
    </article>
  );
}
