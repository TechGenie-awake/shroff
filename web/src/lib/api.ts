/**
 * SHROFF — typed client for the ML API contract (CONTRACTS.md).
 * Every call tries the live API first and falls back to contract-exact
 * fixtures, returning which source answered so the UI can say so honestly.
 */

import type {
  GraphResponse,
  HealthResponse,
  MsmeResponse,
  OcenOffer,
  Persona,
  RailsResponse,
  ScoreResponse,
  ScreenResponse,
  ScreenType,
} from "./types";
import {
  graphFixtures,
  graphPanByMsme,
  healthFixture,
  msmeFixtures,
  ocenFixtures,
  personasFixture,
  railsFixture,
  screenFixture,
  scoreFixtures,
} from "./fixtures";

export const API_BASE =
  process.env.NEXT_PUBLIC_ML_API ?? "http://localhost:8000";

export type DataSource = "live" | "fixture";

export interface Sourced<T> {
  data: T;
  source: DataSource;
}

const TIMEOUT_MS = 2500;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: ctrl.signal,
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

async function withFallback<T>(
  live: () => Promise<T>,
  fixture: () => T
): Promise<Sourced<T>> {
  try {
    return { data: await live(), source: "live" };
  } catch {
    return { data: fixture(), source: "fixture" };
  }
}

/** GET /api/health */
export function getHealth(): Promise<Sourced<HealthResponse>> {
  return withFallback(
    () => request<HealthResponse>("/api/health"),
    () => healthFixture
  );
}

/** GET /api/personas */
export function getPersonas(): Promise<Sourced<Persona[]>> {
  return withFallback(
    () => request<Persona[]>("/api/personas"),
    () => personasFixture
  );
}

/**
 * The live API emits the faithful ReBIT v2 nesting (consent fields under
 * `ConsentDetail`); the UI consumes the flattened artefact. Normalize both.
 */
function normalizeConsent(raw: MsmeResponse["consent"]): MsmeResponse["consent"] {
  const nested = (raw as unknown as Record<string, unknown>)?.["ConsentDetail"];
  if (nested && typeof nested === "object") {
    return {
      ...(nested as object),
      ver: raw.ver,
      txnid: raw.txnid,
      consentId: raw.consentId,
      status: raw.status,
      createTimestamp: raw.createTimestamp,
    } as MsmeResponse["consent"];
  }
  return raw;
}

/** GET /api/msme/{id} */
export function getMsme(id: string): Promise<Sourced<MsmeResponse>> {
  return withFallback(
    async () => {
      const res = await request<MsmeResponse>(
        `/api/msme/${encodeURIComponent(id)}`
      );
      return { ...res, consent: normalizeConsent(res.consent) };
    },
    () => {
      const fx = msmeFixtures[id];
      if (!fx) throw new Error(`Unknown msme_id: ${id}`);
      return fx;
    }
  );
}

/** POST /api/score */
export function postScore(msmeId: string): Promise<Sourced<ScoreResponse>> {
  return withFallback(
    () =>
      request<ScoreResponse>("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msme_id: msmeId }),
      }),
    () => {
      const fx = scoreFixtures[msmeId];
      if (!fx) throw new Error(`Unknown msme_id: ${msmeId}`);
      return fx;
    }
  );
}

/** GET /api/screen?type=...&value=... */
export function getScreen(
  type: ScreenType,
  value: string
): Promise<Sourced<ScreenResponse>> {
  const qs = `?type=${encodeURIComponent(type)}&value=${encodeURIComponent(value)}`;
  return withFallback(
    () => request<ScreenResponse>(`/api/screen${qs}`),
    () => screenFixture(type, value)
  );
}

/** GET /api/graph/{pan} */
export function getGraph(pan: string): Promise<Sourced<GraphResponse>> {
  return withFallback(
    () => request<GraphResponse>(`/api/graph/${encodeURIComponent(pan)}`),
    () => {
      const fx = graphFixtures[pan.trim().toUpperCase()];
      if (!fx) throw new Error(`Unknown pan: ${pan}`);
      return fx;
    }
  );
}

/** POST /api/whatif (optional/stretch endpoint per contract) */
export function postWhatIf(
  msmeId: string,
  overrides: Record<string, number>
): Promise<Sourced<ScoreResponse>> {
  return withFallback(
    () =>
      request<ScoreResponse>("/api/whatif", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msme_id: msmeId, overrides }),
      }),
    () => {
      const fx = scoreFixtures[msmeId];
      if (!fx) throw new Error(`Unknown msme_id: ${msmeId}`);
      return fx;
    }
  );
}

/** GET /api/ocen/offer/{id} — the decision as an OCEN 4.0 loan offer (output rail) */
export function getOcenOffer(id: string): Promise<Sourced<OcenOffer>> {
  return withFallback(
    () => request<OcenOffer>(`/api/ocen/offer/${encodeURIComponent(id)}`),
    () => {
      const fx = ocenFixtures[id];
      if (!fx) throw new Error(`Unknown msme_id: ${id}`);
      return fx;
    }
  );
}

/** GET /api/rails — DataSourceAdapter status registry */
export function getRails(): Promise<Sourced<RailsResponse>> {
  return withFallback(
    () => request<RailsResponse>("/api/rails"),
    () => railsFixture
  );
}

/** Resolve the graph-walk PAN for an msme id (profile PAN when live). */
export function panForMsme(id: string, profilePan?: string): string {
  return profilePan ?? graphPanByMsme[id] ?? id;
}
