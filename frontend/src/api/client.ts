/**
 * Typed API client for the Lumen Studio backend.
 *
 * Types mirror the Pydantic schemas in ``backend/app/models/schemas.py``.
 * The base URL defaults to ``/api/v1`` so the Vite dev-proxy can forward
 * requests to the backend during local development.  Override with
 * ``VITE_API_URL`` for production when the API is on a different origin.
 */

export interface HealthCheck {
  status: string;
  service: string;
}

export interface VersionInfo {
  version: string;
  env: string;
  demo_mode: boolean;
}

export interface Vtable {
  id: number;
  name: string;
  field_name: string;
  base_address: string | null;
  slots: (string | null)[];
  created_at: string;
  updated_at: string;
}

export interface ResolutionMatch {
  line: number;
  column: number;
  expression: string;
  field_name: string;
  slot_index: number;
  resolved_function: string | null;
  note: string;
}

export interface Resolution {
  id: number;
  vtable_id: number;
  vtable_name: string;
  code: string;
  matches: ResolutionMatch[];
  created_at: string;
}

export interface ResolutionSummary {
  id: number;
  vtable_id: number;
  vtable_name: string;
  match_count: number;
  created_at: string;
}

export interface VtableCreateInput {
  name: string;
  field_name: string;
  base_address?: string;
  slots: (string | null)[];
}

export interface ResolutionCreateInput {
  vtable_id: number;
  code: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (resp.status === 204) {
    return undefined as unknown as T;
  }

  const body = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    throw new ApiError(resp.status, body.detail || body.message || "Unknown error");
  }

  return body as T;
}

export const api = {
  // Health
  health: () => request<HealthCheck>("/health"),
  version: () => request<VersionInfo>("/version"),

  // Vtables
  createVtable: (data: VtableCreateInput) =>
    request<Vtable>("/vtables", { method: "POST", body: JSON.stringify(data) }),
  listVtables: () => request<Vtable[]>("/vtables"),
  getVtable: (id: number) => request<Vtable>(`/vtables/${id}`),
  deleteVtable: (id: number) =>
    request<void>(`/vtables/${id}`, { method: "DELETE" }),

  // Resolutions
  createResolution: (data: ResolutionCreateInput) =>
    request<Resolution>("/resolutions", { method: "POST", body: JSON.stringify(data) }),
  listResolutions: () => request<ResolutionSummary[]>("/resolutions"),
  getResolution: (id: number) => request<Resolution>(`/resolutions/${id}`),
};