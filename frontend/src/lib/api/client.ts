import { notifyUnauthorized } from "../auth/session-events.ts";
import { getAccessToken, getSessionEpoch } from "../auth/token-store.ts";
import { frontendEnv } from "./env.ts";
import { ApiClientError, type ApiErrorData, extractFastApiValidationArray } from "./errors.ts";

export { ApiClientError, type ApiErrorData };

export type ApiAuthMode = "bearer" | "none";

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  headers?: Record<string, string> | undefined;
  signal?: AbortSignal | undefined;
  baseUrl?: string | undefined;
  authMode?: ApiAuthMode | undefined;
  skipUnauthorizedHandler?: boolean | undefined;
}

const SCHEME_PREFIX = /^[a-zA-Z][a-zA-Z\d+\-.]*:/;

function buildUrl(baseUrl: string, path: string): string {
  const trimmedPath = path.trim();
  if (!trimmedPath) {
    throw new Error("API request path must not be empty.");
  }
  if (SCHEME_PREFIX.test(trimmedPath) || trimmedPath.startsWith("//")) {
    throw new Error("API request path must be a relative API route, not an absolute URL.");
  }

  const cleanBase = baseUrl.replace(/\/+$/, "");
  let normalizedPath = trimmedPath.startsWith("/") ? trimmedPath : `/${trimmedPath}`;

  if (
    (cleanBase === "/api/v1" || cleanBase.endsWith("/api/v1")) &&
    (normalizedPath === "/api/v1" ||
      normalizedPath.startsWith("/api/v1/") ||
      normalizedPath.startsWith("/api/v1?"))
  ) {
    normalizedPath = normalizedPath.slice("/api/v1".length);
  }

  return `${cleanBase}${normalizedPath}`;
}

function isAbortFailure(error: unknown, signal?: AbortSignal): boolean {
  if (signal?.aborted) {
    return true;
  }
  return (error instanceof DOMException || error instanceof Error) && error.name === "AbortError";
}

function parseNonNegativeInt(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isInteger(value) && value >= 0) {
    return value;
  }
  if (typeof value === "string" && /^\d+$/.test(value)) {
    return Number.parseInt(value, 10);
  }
  return undefined;
}

export async function apiRequest<TResponse>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<TResponse> {
  const baseUrl = options.baseUrl ?? frontendEnv.apiBaseUrl;
  const headers = new Headers(options.headers);
  const authMode: ApiAuthMode = options.authMode ?? "bearer";

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (authMode === "none") {
    headers.delete("Authorization");
  } else {
    const token = getAccessToken();
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
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

  const requestUrl = buildUrl(baseUrl, path);
  const requestEpoch = getSessionEpoch();
  const hadAuthHeader = headers.has("Authorization");

  let response: Response;
  try {
    response = await fetch(requestUrl, init);
  } catch (error: unknown) {
    if (isAbortFailure(error, options.signal)) {
      throw error;
    }
    throw new ApiClientError({
      status: 0,
      code: "NETWORK_ERROR",
      message: "Unable to reach the server. Check your network connection and try again.",
    });
  }

  const responseRequestId = response.headers.get("X-Request-ID") ?? undefined;
  const headerRetryAfter = parseNonNegativeInt(response.headers.get("Retry-After"));

  if (!response.ok) {
    let parsedError: Record<string, unknown> | null = null;
    try {
      const errorText = await response.text();
      if (errorText.trim() !== "") {
        const json: unknown = JSON.parse(errorText);
        if (typeof json === "object" && json !== null) {
          parsedError = json as Record<string, unknown>;
        }
      }
    } catch {
      parsedError = null;
    }

    const errorObj =
      parsedError && typeof parsedError.error === "object" && parsedError.error !== null
        ? (parsedError.error as Record<string, unknown>)
        : null;

    // Defensive support if raw FastAPI HTTPValidationError `{ detail: [...] }` ever bypasses the custom handler.
    const fastApiDetailArray =
      errorObj === null && parsedError && Array.isArray(parsedError.detail)
        ? parsedError.detail
        : null;

    const code =
      errorObj && typeof errorObj.code === "string"
        ? errorObj.code
        : fastApiDetailArray !== null
          ? "VALIDATION_ERROR"
          : `HTTP_${response.status}`;

    const message =
      errorObj && typeof errorObj.message === "string"
        ? errorObj.message
        : fastApiDetailArray !== null
          ? "Request validation failed."
          : `Request failed with status ${response.status}.`;

    const details =
      errorObj !== null
        ? errorObj.details
        : fastApiDetailArray !== null
          ? extractFastApiValidationArray(fastApiDetailArray)
          : undefined;

    const bodyRequestId =
      errorObj && typeof errorObj.request_id === "string" ? errorObj.request_id : undefined;
    const effectiveRequestId = bodyRequestId ?? responseRequestId;

    const detailsRecord =
      typeof details === "object" && details !== null && !Array.isArray(details)
        ? (details as Record<string, unknown>)
        : null;
    const bodyRetryAfter =
      response.status === 429 && detailsRecord !== null
        ? parseNonNegativeInt(detailsRecord.retry_after_seconds)
        : undefined;
    const effectiveRetryAfter = headerRetryAfter ?? bodyRetryAfter;

    if (
      response.status === 401 &&
      !options.skipUnauthorizedHandler &&
      authMode !== "none" &&
      hadAuthHeader
    ) {
      notifyUnauthorized(requestEpoch);
    }

    const errData: ApiErrorData = {
      status: response.status,
      code,
      message,
      details,
      ...(effectiveRequestId !== undefined ? { requestId: effectiveRequestId } : {}),
      ...(effectiveRetryAfter !== undefined ? { retryAfterSeconds: effectiveRetryAfter } : {}),
    };
    throw new ApiClientError(errData);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as TResponse;
  }

  const bodyText = await response.text();
  if (bodyText.trim() === "") {
    return undefined as TResponse;
  }

  try {
    return JSON.parse(bodyText) as TResponse;
  } catch {
    throw new ApiClientError({
      status: response.status,
      code: "INVALID_RESPONSE",
      message: "Received an unexpected response format from the server.",
      ...(responseRequestId !== undefined ? { requestId: responseRequestId } : {}),
    });
  }
}
