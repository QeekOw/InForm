// Small fetch wrapper for authenticated calls to the FastAPI backend
// (Accounts & History, issues #41-#44). The backend and frontend are on
// different origins (Vercel/Render), so every authenticated call must send
// `credentials: "include"` for the session cookie to go along with it —
// centralized here so no call site can forget it.

import { API_URL } from "./config";
import { loadJSON, SESSION_KEYS } from "./session";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API returned ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(res: Response): Promise<unknown> {
  try {
    const body = await res.json();
    return body?.detail ?? body;
  } catch {
    return res.statusText;
  }
}

/** JSON fetch against the backend, sending both session cookie and Authorization header.
 * Throws ApiError (with the parsed `detail`) on a non-2xx response. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = typeof window !== "undefined" ? loadJSON<string>(SESSION_KEYS.authToken) : null;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorDetail(res));
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}
