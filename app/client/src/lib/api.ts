/** Small typed fetch helper for the app's own Express routes. */
export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  const body: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const b = (body ?? {}) as { error?: string; detail?: string };
    throw new ApiError(b.error ?? `Request failed (${res.status})`, res.status, b.detail);
  }
  return body as T;
}

export type Row = Record<string, unknown>;
