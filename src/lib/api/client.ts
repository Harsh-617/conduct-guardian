/**
 * Fetch client for the Conduct Guardian backend.
 *
 * Every call throws `ApiError` carrying the backend's `{code, message,
 * retryable}`. `retryable` is what the UI uses to choose between "Try again"
 * and a terminal error — PRD §9 requires a clear retry state, never a blank
 * crash.
 */

import type {
  AgencyResponse,
  CoachingResponse,
  DashboardStats,
  HardshipResponse,
  HealthResponse,
  LedgerPage,
  ScreenRequest,
  ScreenResponse,
  TimelineResponse,
  VerifyResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly code: string;
  readonly retryable: boolean;
  readonly status: number;

  constructor(message: string, code: string, retryable: boolean, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = retryable;
    this.status = status;
  }
}

// Cold starts on Render's free tier take 30-50s (see below); /coaching can
// also fan out several sequential LLM calls on a cache miss. Without a
// client-side ceiling, a hung backend leaves the UI stuck on the loading
// skeleton forever with no path to the retry state.
const REQUEST_TIMEOUT_MS = 60_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      // Next 15 caches fetch by default. These are live compliance numbers —
      // a cached dashboard showing yesterday's counts during a demo is worse
      // than a slightly slower one.
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    // Network-level failure, or our own timeout abort. On Render's free tier
    // the backend sleeps after ~15 min idle and the next request takes
    // 30-50s, so this is very often a cold start rather than a real outage.
    // Always retryable.
    throw new ApiError(
      "Could not reach the screening service. It may be waking up.",
      "network_error",
      true,
      0,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let code = "http_error";
    let message = `Request failed with status ${response.status}`;
    let retryable = response.status >= 500 || response.status === 429;

    try {
      const body = await response.json();
      // FastAPI nests HTTPException payloads under `detail`; the global
      // handler returns ErrorBody at the top level. Accept both.
      const err = body?.detail ?? body;
      if (err && typeof err === "object") {
        code = err.code ?? code;
        message = err.message ?? message;
        if (typeof err.retryable === "boolean") retryable = err.retryable;
      }
    } catch {
      // Non-JSON error body — keep the defaults.
    }

    throw new ApiError(message, code, retryable, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  /** Live Screening. Real Groq call — expect 6-7s typical, up to 11-14s at p95. */
  screen: (body: ScreenRequest) =>
    request<ScreenResponse>("/screen", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  dashboardStats: () => request<DashboardStats>("/dashboard/stats"),

  timeline: (accountExternalId: string) =>
    request<TimelineResponse>(`/timeline/${encodeURIComponent(accountExternalId)}`),

  /**
   * `violationsOnly` is what the dashboard's Recent Flags panel wants — a
   * panel called "Recent Flags" must not list clean entries, and filtering
   * the newest N in the browser would show an empty list whenever the last
   * few screens happened to be clean.
   */
  ledger: (page = 1, pageSize = 25, violationsOnly = false) =>
    request<LedgerPage>(
      `/ledger?page=${page}&page_size=${pageSize}` +
        (violationsOnly ? "&violations_only=true" : ""),
    ),

  /** Powers "Verify Chain Integrity" — really recomputes every hash. */
  verifyLedger: () => request<VerifyResponse>("/ledger/verify", { method: "POST" }),

  coaching: (refresh = false) =>
    request<CoachingResponse>(`/coaching${refresh ? "?refresh=true" : ""}`),

  hardship: () => request<HardshipResponse>("/hardship"),

  agencies: () => request<AgencyResponse>("/agencies"),
};
