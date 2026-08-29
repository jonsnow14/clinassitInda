import type {
  ClinicalCard,
  Expert,
  Health,
  Hospital,
  Pharmacy,
  SosStatus,
  Track,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
      else detail = JSON.stringify(body);
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Health>("/v1/health"),
  toHindi: (text: string) => req<{ text: string; model: string }>("/v1/script/hindi", {
    method: "POST",
    body: JSON.stringify({ text }),
  }),
  consult: (text: string) =>
    req<ClinicalCard>("/v1/clinical/consult", {
      method: "POST",
      body: JSON.stringify({ text, phc_id: "phc-purnia" }),
    }),
  beds: (need: string) =>
    req<{ hospitals: Hospital[]; need: string; note?: string }>(`/v1/beds?need=${need}`),
  transportDispatch: () =>
    req<Track>("/v1/transport/dispatch", {
      method: "POST",
      body: JSON.stringify({ kind: "ambulance", need_oxygen: true }),
    }),
  transportTrack: (id: string) => req<Track>(`/v1/transport/${id}/track`),
  pharmacy: (meds = "aspirin,clopidogrel") =>
    req<{ pharmacies: Pharmacy[]; note: string; meds: string[] }>(
      `/v1/pharmacy?meds=${encodeURIComponent(meds)}`,
    ),
  pharmacyDispatch: (pharmacy_id: string, meds: string[]) =>
    req<Track>("/v1/pharmacy/dispatch", {
      method: "POST",
      body: JSON.stringify({ pharmacy_id, meds }),
    }),
  courierTrack: (id: string) => req<Track>(`/v1/courier/${id}/track`),
  experts: () => req<{ experts: Expert[] }>("/v1/experts"),
  expertConsult: (id: string, case_summary: string) =>
    req<{ status: string; expert: Expert; note: string }>(`/v1/experts/${id}/consult`, {
      method: "POST",
      body: JSON.stringify({ case_summary }),
    }),
  sos: (reason: "security" | "community", note: string) =>
    req<SosStatus>("/v1/sos", {
      method: "POST",
      body: JSON.stringify({ reason, note }),
    }),
  sosStatus: (id: string) => req<SosStatus>(`/v1/sos/${id}`),
};
