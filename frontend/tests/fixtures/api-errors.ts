import { HttpResponse } from "msw";

export interface BackendErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}

export function createErrorEnvelope(
  code: string,
  message: string,
  details: Record<string, unknown> = {},
  requestId = "req-test-001"
): BackendErrorEnvelope {
  return {
    error: {
      code,
      message,
      details,
      request_id: requestId,
    },
  };
}

export const apiErrorFixtures = {
  unauthorized: () =>
    HttpResponse.json(
      createErrorEnvelope(
        "UNAUTHORIZED",
        "Authentication credentials were not provided or are invalid.",
        {},
        "req-401"
      ),
      { status: 401 }
    ),
  forbidden: () =>
    HttpResponse.json(
      createErrorEnvelope(
        "FORBIDDEN",
        "You do not have permission to perform this action.",
        {},
        "req-403"
      ),
      { status: 403 }
    ),
  notFound: (code = "RESOURCE_NOT_FOUND") =>
    HttpResponse.json(
      createErrorEnvelope(code, "The requested resource was not found.", {}, "req-404"),
      { status: 404 }
    ),
  conflict: (code = "STATE_CONFLICT", details: Record<string, unknown> = {}) =>
    HttpResponse.json(createErrorEnvelope(code, "A state conflict occurred.", details, "req-409"), {
      status: 409,
    }),
  validationError: (details: Record<string, string[]> = { field: ["Field required."] }) =>
    HttpResponse.json(
      createErrorEnvelope("VALIDATION_ERROR", "Request validation failed.", details, "req-422"),
      { status: 422 }
    ),
  rateLimited: (retryAfterSeconds = 60) =>
    HttpResponse.json(
      createErrorEnvelope(
        "RATE_LIMIT_EXCEEDED",
        "Too many requests. Please try again later.",
        {},
        "req-429"
      ),
      {
        status: 429,
        headers: { "Retry-After": String(retryAfterSeconds) },
      }
    ),
  internalError: () =>
    HttpResponse.json(
      createErrorEnvelope("INTERNAL_ERROR", "An internal server error occurred.", {}, "req-500"),
      { status: 500 }
    ),
} as const;
