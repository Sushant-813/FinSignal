import { getAccessToken } from "../auth/token-store.ts";
import { frontendEnv } from "./env.ts";

export interface ApiErrorData {
  readonly status: number;
  readonly code: string;
  readonly message: string;
  readonly details?: unknown;
  readonly requestId?: string | undefined;
  readonly retryAfterSeconds?: number | undefined;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;
  readonly requestId?: string | undefined;
  readonly retryAfterSeconds?: number | undefined;

  constructor(data: ApiErrorData) {
    super(data.message);
    this.name = "ApiClientError";
    this.status = data.status;
    this.code = data.code;
    this.details = data.details;
    this.requestId = data.requestId;
    this.retryAfterSeconds = data.retryAfterSeconds;
  }
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  baseUrl?: string;
}

function buildUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<TResponse> {
  const baseUrl = options.baseUrl ?? frontendEnv.apiBaseUrl;
  const headers = new Headers(options.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let requestBody: BodyInit | undefined;
  if (options.body instanceof FormData) {
    requestBody = options.body;
  } else if (options.body !== undefined) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    requestBody = JSON.stringify(options.body);
  }

  const init: RequestInit = {
    method: options.method ?? "GET",
    headers,
  };
  if (requestBody !== undefined) {
    init.body = requestBody;
  }
  if (options.signal !== undefined) {
    init.signal = options.signal;
  }

  const response = await fetch(buildUrl(baseUrl, path), init);

  const responseRequestId = response.headers.get("X-Request-ID") ?? undefined;
  const retryAfterRaw = response.headers.get("Retry-After");
  const retryAfterSeconds =
    retryAfterRaw !== null && /^\d+$/.test(retryAfterRaw)
      ? Number.parseInt(retryAfterRaw, 10)
      : undefined;

  if (!response.ok) {
    let parsedError: Record<string, unknown> | null = null;
    try {
      const json: unknown = await response.json();
      if (typeof json === "object" && json !== null) {
        parsedError = json as Record<string, unknown>;
      }
    } catch {
      parsedError = null;
    }

    const errorObj =
      parsedError && typeof parsedError.error === "object" && parsedError.error !== null
        ? (parsedError.error as Record<string, unknown>)
        : null;

    const code =
      errorObj && typeof errorObj.code === "string" ? errorObj.code : `HTTP_${response.status}`;
    const message =
      errorObj && typeof errorObj.message === "string"
        ? errorObj.message
        : `Request failed with status ${response.status}.`;
    const bodyRequestId =
      errorObj && typeof errorObj.request_id === "string" ? errorObj.request_id : undefined;
    const effectiveRequestId = bodyRequestId ?? responseRequestId;

    const errData: ApiErrorData = {
      status: response.status,
      code,
      message,
      details: errorObj?.details,
      ...(effectiveRequestId !== undefined ? { requestId: effectiveRequestId } : {}),
      ...(retryAfterSeconds !== undefined ? { retryAfterSeconds } : {}),
    };
    throw new ApiClientError(errData);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
