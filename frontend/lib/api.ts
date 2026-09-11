// ============================================================
// Centralized API client (single source of truth).
//
// Base URLs come from environment configuration:
//   NEXT_PUBLIC_API_BASE_URL  e.g. http://localhost:8000/api/v1
//   NEXT_PUBLIC_BACKEND_URL   e.g. http://localhost:8000
// with local fallbacks so the app still runs without .env.local.
// No component builds its own URLs; nothing is hardcoded beyond
// these documented local defaults.
// ============================================================

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '');
const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '');

// ============================================================
// Types (mirror the verified FastAPI response shapes)
// ============================================================

export type User = {
  id: number;
  email: string;
  role: 'admin' | 'organization' | string;
  organization_id: number | null;
};

export type Classification = {
  predicted_class: string | null;
  class_probabilities?: Record<string, number> | null;
  classification_confidence: number | null;
  model_version: string | null;
  feature_version?: string;
  reason?: string;
};

export type Abnormality = {
  baseline_available: boolean;
  abnormality_score: number | null;
  abnormality_status: string;
  reason?: string | null;
};

export type EventRisk = {
  risk_score: number;
  risk_level: string;
  risk_factors: Record<string, number>;
  method?: string;
  missing_context: string[];
  abnormality: Abnormality;
};

export type EventContext = {
  osm_context_available?: boolean;
  osm_reason?: string;
  satellite_context_available?: boolean;
  ndvi?: number | null;
  land_cover?: string | null;
  vegetation_fraction?: number | null;
  built_up_fraction?: number | null;
  satellite_image_reference?: string | null;
  provider?: string;
  acquisition_date?: string;
  reason?: string;
  landuse_class?: string;
  nearby_industrial_count?: number;
  nearby_facility_count?: number;
  distance_to_industrial_m?: number | null;
  distance_to_residential_m?: number | null;
  nearby_facility_names?: string[];
  [key: string]: unknown;
};

export type ThermalEvent = {
  id: string;
  latitude: number;
  longitude: number;
  is_demo: boolean;
  start_time: string;
  last_seen_time: string;
  duration_hours: number;
  detection_count: number;
  mean_frp: number;
  max_frp: number;
  mean_brightness: number;
  max_brightness?: number;
  spatial_spread_km?: number;
  night_fraction?: number;
  persistence_days: number;
  status?: string;
  detection_ids?: string[];
  classification: Classification;
  context: EventContext;
  risk: EventRisk;
  history?: Record<string, unknown>;
  features?: Record<string, unknown>;
};

export type ModelStatus = {
  training_ready: boolean;
  model_available: boolean;
  model_version: string | null;
  eligible_labeled_rows: number;
  reason: string;
  feature_version: string;
};

export type Alert = {
  id: number;
  event_id: string;
  organization_id: number | null;
  risk_level: string;
  created_at: string;
  status: 'open' | 'acknowledged' | string;
  notification_status: string;
  is_demo: boolean;
};

export type FirmsStatus = {
  available: boolean;
  last_success: string | null;
  reason: string | null;
  configured: boolean;
  mode: 'DEMO' | 'REAL' | string;
};

export type FirmsSyncResponse = {
  ingested: number;
  rejected: number;
  events: number;
  osm_context_available_events: number;
  satellite_context_available_events: number;
};

export type Evidence = {
  event: ThermalEvent;
  detected_facts: Record<string, unknown>[];
  model_interpretation: Classification;
  risk_assessment: EventRisk;
};

export type CopilotResponse = {
  answer: string;
  mode: 'ollama' | 'deterministic_fallback' | string;
  event_ids: string[];
};

export type TrendPoint = { date: string; events: number; mean_risk: number };
export type AnalyticsResponse = TrendPoint[] | { available: false; reason: string; window_days?: number };
export type AreaResult = { name: string; bounds: number[]; source: string };
export type Organization = { id: number; name: string; email: string };
export type Assignment = {
  id: number;
  organization_id: number;
  area_name: string;
  bounds: number[];
  minimum_alert_level?: string;
};

// ============================================================
// Session token storage.
//
// sessionStorage keeps the token out of persistent storage and
// out of the URL/console; it survives reloads within the tab
// but dies with the tab. Key exported for logout cleanup.
// ============================================================

const TOKEN_KEY = 'thermaguard.token';

export function getStoredToken(): string {
  if (typeof window === 'undefined') return '';
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

export function storeToken(token: string): void {
  if (typeof window === 'undefined') return;
  try {
    if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage unavailable (private mode); session stays in memory only.
  }
}

// ============================================================
// Core request helper.
//
// - attaches Bearer token automatically when present
// - supports GET/POST/PUT/PATCH/DELETE
// - enforces a request timeout (AbortController)
// - parses FastAPI error bodies safely (string detail, 422 detail
//   arrays, empty or non-JSON bodies) into readable messages
// - never logs or echoes the token
// ============================================================

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const DEFAULT_TIMEOUT_MS = 20000;

type RequestMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

async function request<T>(
  path: string,
  {
    method = 'GET',
    token,
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
  }: { method?: RequestMethod; token?: string; body?: unknown; timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    // Absolute URLs (health probe) bypass the API base prefix.
    const url = /^https?:\/\//.test(path) ? path : API_BASE + path;
    const response = await fetch(url, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      signal: controller.signal,
    });
    return await parse<T>(response);
  } catch (error) {
    // A received HTTP error is not a connectivity failure (especially 401).
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      throw new ApiError(
        `The request timed out after ${Math.round(timeoutMs / 1000)} s. Retry the request.`,
        504,
      );
    }
    throw new ApiError(
      'Cannot reach the backend. Check the API address, network connection, and CORS configuration.',
      0,
    );
  } finally {
    clearTimeout(timer);
  }

}

async function parse<T>(response: Response): Promise<T> {
  // Read the body once, defensively: it may be empty, HTML from a
  // proxy, or FastAPI's {"detail": ...} envelope.
  const raw = await response.text();

  if (!response.ok) {
    throw new ApiError(readableError(response.status, raw), response.status);
  }

  if (!raw) {
    throw new ApiError('The server returned an empty response.', response.status);
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    throw new ApiError('The server returned a response that is not valid JSON.', response.status);
  }
}

function readableError(status: number, raw: string): string {
  let detail: unknown = null;
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      detail = parsed.detail ?? null;
    } catch {
      // Non-JSON body (proxy HTML page, plain text).
    }
  }

  if (typeof detail === 'string' && detail) return detail;

  // FastAPI 422 validation errors arrive as an array of objects.
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : '';
    return first.msg ? `${field ? field + ': ' : ''}${first.msg}` : 'The request was rejected as invalid.';
  }

  if (status === 401) return 'Authentication required. Sign in again.';
  if (status === 403) return 'You do not have permission for this action.';
  if (status === 404) return 'The requested item was not found.';
  if (status >= 500) return 'The server encountered an error. Try again.';
  return `Request failed (HTTP ${status}).`;
}

// Convenience wrappers so callers never repeat fetch options.
export function apiGet<T>(path: string, token?: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, { method: 'GET', token, timeoutMs });
}

export function apiPost<T>(path: string, body: unknown, token?: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, { method: 'POST', token, body: body ?? {}, timeoutMs });
}

export function apiPut<T>(path: string, body: unknown, token?: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, { method: 'PUT', token, body: body ?? {}, timeoutMs });
}

export function apiPatch<T>(path: string, body: unknown, token?: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, { method: 'PATCH', token, body: body ?? {}, timeoutMs });
}

export function apiDelete<T>(path: string, token?: string, timeoutMs?: number): Promise<T> {
  return request<T>(path, { method: 'DELETE', token, timeoutMs });
}

// Unauthenticated health probe against the backend origin.
export function fetchHealth(timeoutMs = 6000): Promise<{ status: string; project: string; demo_mode: boolean }> {
  return request<{ status: string; project: string; demo_mode: boolean }>(BACKEND_URL + '/health', {
    timeoutMs,
  });
}
