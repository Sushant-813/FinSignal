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

export function isApiClientError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError;
}

export function isNetworkError(error: unknown): boolean {
  return isApiClientError(error) && (error.status === 0 || error.code === "NETWORK_ERROR");
}

export function isUnauthorizedError(error: unknown): boolean {
  return isApiClientError(error) && error.status === 401;
}

export function isForbiddenError(error: unknown): boolean {
  return isApiClientError(error) && error.status === 403;
}

/**
 * Normalizes `422` validation details into `{ fieldName: string[] }`.
 * Supports FinSignal's `{ error: { details: Record<string, string[]> } }` envelope
 * as well as FastAPI `HTTPValidationError` item arrays when encountered defensively.
 */
export function extractFieldErrors(error: unknown): Record<string, string[]> {
  if (!isApiClientError(error) || typeof error.details !== "object" || error.details === null) {
    return {};
  }

  if (Array.isArray(error.details)) {
    return extractFastApiValidationArray(error.details);
  }

  const result: Record<string, string[]> = {};
  for (const [field, value] of Object.entries(error.details)) {
    if (typeof value === "string" && value.trim()) {
      result[field] = [value];
    } else if (Array.isArray(value)) {
      const messages = value.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0
      );
      if (messages.length > 0) {
        result[field] = messages;
      }
    }
  }
  return result;
}

export function extractFastApiValidationArray(items: readonly unknown[]): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const item of items) {
    if (typeof item !== "object" || item === null) {
      continue;
    }
    const record = item as Record<string, unknown>;
    const msg = typeof record.msg === "string" ? record.msg.trim() : "";
    if (!msg) {
      continue;
    }
    const loc = Array.isArray(record.loc) ? record.loc : [];
    const lastSegment = loc[loc.length - 1];
    const field =
      typeof lastSegment === "string" || typeof lastSegment === "number"
        ? String(lastSegment)
        : "non_field";
    const existing = result[field];
    if (existing) {
      existing.push(msg);
    } else {
      result[field] = [msg];
    }
  }
  return result;
}

export function getUserFriendlyErrorMessage(
  error: unknown,
  fallback = "An unexpected error occurred. Please try again."
): string {
  if (!isApiClientError(error)) {
    return fallback;
  }

  if (isNetworkError(error)) {
    return "Unable to reach the server. Check your network connection and try again.";
  }

  if (error.status === 429) {
    return error.retryAfterSeconds !== undefined
      ? `Too many requests. Please wait ${error.retryAfterSeconds} seconds before trying again.`
      : "Too many requests. Please wait a moment before trying again.";
  }

  if (error.status >= 500) {
    return "A server error occurred while processing your request. Please try again later.";
  }

  return error.message || fallback;
}
