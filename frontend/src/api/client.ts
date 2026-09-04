/**
 * Tiny typed fetch wrapper.
 * Reads VITE_API_BASE at build time, falls back to localhost:8000.
 */

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

export const WS_BASE =
  (import.meta.env.VITE_WS_BASE as string | undefined) ??
  API_BASE.replace(/^http/, "ws");

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** when true, returns the raw text instead of parsing JSON. Used for TwiML. */
  raw?: boolean;
};

export async function request<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, signal, raw = false } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body
      ? { "Content-Type": "application/json", Accept: "application/json" }
      : { Accept: "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      try {
        payload = await res.text();
      } catch {
        // ignore
      }
    }
    const message =
      (payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : null) ?? `Request failed: ${res.status}`;
    throw new ApiError(res.status, payload, message);
  }

  if (raw) {
    return (await res.text()) as T;
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export { API_BASE };
