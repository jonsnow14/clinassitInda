import type {
  ClinicalCard,
  Expert,
  Health,
  Hospital,
  Pharmacy,
  SosStatus,
  Track,
} from "./types";

/**
 * Base URL for public backend API calls.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * Generic helper for executing JSON fetch requests against the backend.
 *
 * @template T - Expected JSON response shape.
 * @param {string} path - Relative API endpoint path.
 * @param {RequestInit} [init] - Optional fetch initialization options.
 * @returns {Promise<T>} Resolves with parsed response body.
 * @throws {Error} Throws if HTTP response status is not OK.
 */
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

/**
 * API client methods for ClinAssistIndia backend services.
 */
export const api = {
  /** Checks system health, key configuration, and vector store readiness. */
  health: () => req<Health>("/v1/health"),

  /**
   * Converts Hinglish/Roman script input to Hindi Devanagari using the Mayura service.
   *
   * @param {string} text - Input text in Roman script.
   */
  toHindi: (text: string) => req<{ text: string; model: string }>("/v1/script/hindi", {
    method: "POST",
    body: JSON.stringify({ text }),
  }),

  /**
   * Submits a clinical query for RAG-based diagnosis and treatment protocol generation.
   *
   * @param {string} text - Case description or patient symptoms.
   */
  consult: (text: string) =>
    req<ClinicalCard>("/v1/clinical/consult", {
      method: "POST",
      body: JSON.stringify({ text, phc_id: "phc-purnia" }),
    }),

  /**
   * Searches nearby hospital directory for bed availability matching specific needs.
   *
   * @param {string} need - Required bed type (e.g. "icu").
   */
  beds: (need: string) =>
    req<{ hospitals: Hospital[]; need: string; note?: string }>(`/v1/beds?need=${need}`),

  /**
   * Dispatches emergency transport vehicle (e.g. ambulance with oxygen).
   */
  transportDispatch: () =>
    req<Track>("/v1/transport/dispatch", {
      method: "POST",
      body: JSON.stringify({ kind: "ambulance", need_oxygen: true }),
    }),

  /**
   * Polls tracking status for active transport dispatch.
   *
   * @param {string} id - Trip ID.
   */
  transportTrack: (id: string) => req<Track>(`/v1/transport/${id}/track`),

  /**
   * Queries nearby pharmacies for stock availability of requested medicines.
   *
   * @param {string} [meds="aspirin,clopidogrel"] - Comma-separated list of required medications.
   */
  pharmacy: (meds = "aspirin,clopidogrel") =>
    req<{ pharmacies: Pharmacy[]; note: string; meds: string[] }>(
      `/v1/pharmacy?meds=${encodeURIComponent(meds)}`,
    ),

  /**
   * Dispatches volunteer courier delivery for medicines from selected pharmacy.
   *
   * @param {string} pharmacy_id - Target pharmacy ID.
   * @param {string[]} meds - List of medicine names to collect.
   */
  pharmacyDispatch: (pharmacy_id: string, meds: string[]) =>
    req<Track>("/v1/pharmacy/dispatch", {
      method: "POST",
      body: JSON.stringify({ pharmacy_id, meds }),
    }),

  /**
   * Polls tracking status for pharmacy courier dispatch.
   *
   * @param {string} id - Courier trip ID.
   */
  courierTrack: (id: string) => req<Track>(`/v1/courier/${id}/track`),

  /** Retrieves available medical expert specialists directory. */
  experts: () => req<{ experts: Expert[] }>("/v1/experts"),

  /**
   * Requests expert tele-consultation for a clinical case.
   *
   * @param {string} id - Expert ID.
   * @param {string} case_summary - Summary diagnosis or patient presentation.
   */
  expertConsult: (id: string, case_summary: string) =>
    req<{ status: string; expert: Expert; note: string }>(`/v1/experts/${id}/consult`, {
      method: "POST",
      body: JSON.stringify({ case_summary }),
    }),

  /**
   * Triggers emergency SOS alert.
   *
   * @param {"security" | "community"} reason - Type of SOS emergency.
   * @param {string} note - Emergency context details.
   */
  sos: (reason: "security" | "community", note: string) =>
    req<SosStatus>("/v1/sos", {
      method: "POST",
      body: JSON.stringify({ reason, note }),
    }),

  /**
   * Retrieves SOS alert status.
   *
   * @param {string} id - SOS alert ID.
   */
  sosStatus: (id: string) => req<SosStatus>(`/v1/sos/${id}`),
};
