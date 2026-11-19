/* Typed API client with automatic token refresh on 401. */

const TOKEN_KEY = "triagedesk.auth";

interface AuthData {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; name: string; role: string };
}

export function loadAuth(): AuthData | null {
  try {
    return JSON.parse(localStorage.getItem(TOKEN_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveAuth(data: AuthData | null): void {
  if (data) localStorage.setItem(TOKEN_KEY, JSON.stringify(data));
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const auth = loadAuth();
  if (!auth?.refresh_token) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const r = await fetch("/api/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: auth.refresh_token }),
        });
        if (!r.ok) return false;
        const data = (await r.json()) as AuthData;
        saveAuth(data);
        return true;
      } catch {
        return false;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const auth = loadAuth();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) headers["Authorization"] = `Bearer ${auth.access_token}`;

  let resp = await fetch(path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (resp.status === 401 && (await tryRefresh())) {
    const fresh = loadAuth();
    headers["Authorization"] = `Bearer ${fresh!.access_token}`;
    resp = await fetch(path, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? data);
    } catch { /* keep default */ }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
};
