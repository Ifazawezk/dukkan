// Small fetch wrapper for the Dukkan API. All paths are relative to /api.

const TOKEN_KEY = "dukkan.token";

export class ApiError extends Error {
  status: number;
  code?: string;
  context?: Record<string, unknown>;

  constructor(status: number, message: string, code?: string, context?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = code;
    this.context = context;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Private windows can refuse storage; the session then lasts until reload.
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  query?: Query;
  body?: unknown;
  form?: Record<string, string>;
}

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const search = params.toString();
  return `/api${path}${search ? `?${search}` : ""}`;
}

async function errorFrom(response: Response): Promise<ApiError> {
  let message = response.statusText || "Request failed";
  let code: string | undefined;
  let context: Record<string, unknown> | undefined;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      // FastAPI validation errors: show the first one with its field name.
      const first = body.detail[0];
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
      message = field ? `${field}: ${first.msg}` : first.msg;
    }
    code = body.code;
    context = body.context;
  } catch {
    // Not JSON; keep the status text.
  }
  return new ApiError(response.status, message, code, context);
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    body = new URLSearchParams(options.form);
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (options.body !== undefined) {
    body = JSON.stringify(options.body);
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? (body ? "POST" : "GET"),
    headers,
    body,
  });

  if (response.status === 401 && token) {
    window.dispatchEvent(new Event("dukkan:unauthorized"));
  }
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? response.json() : response.text()) as Promise<T>;
}

/** Download a CSV report with the user's token and save it under the server's file name. */
export async function downloadFile(path: string, query?: Query) {
  const token = getToken();
  const response = await fetch(buildUrl(path, query), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw await errorFrom(response);
  const disposition = response.headers.get("content-disposition") ?? "";
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "report.csv";
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
