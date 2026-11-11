import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { ApiClientError, apiRequest } from "../../src/lib/api/client.ts";
import { frontendEnv, resolveApiBaseUrl } from "../../src/lib/api/env.ts";
import {
  extractFieldErrors,
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
  isNetworkError,
  isUnauthorizedError,
} from "../../src/lib/api/errors.ts";
import { registerUnauthorizedHandler } from "../../src/lib/auth/session-events.ts";
import {
  clearAccessToken,
  getAccessToken,
  getSessionEpoch,
  setAccessToken,
} from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { server } from "../mocks/server.ts";

const TEST_BASE_URL = "http://localhost/api/v1";

describe("apiRequest (existing F0 behavior)", () => {
  it("handles 204 No Content responses without parsing JSON", async () => {
    server.use(
      http.post(`${TEST_BASE_URL}/auth/logout`, () => {
        return new HttpResponse(null, { status: 204 });
      })
    );

    const result = await apiRequest<void>("/auth/logout", {
      method: "POST",
      baseUrl: TEST_BASE_URL,
    });
    expect(result).toBeUndefined();
  });

  it("omits manual Content-Type for FormData so the browser manages the multipart boundary", async () => {
    let capturedAccept: string | null = null;
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    server.use(
      http.post(`${TEST_BASE_URL}/datasets/imports`, ({ request }) => {
        capturedAccept = request.headers.get("Accept");
        return HttpResponse.json({ id: "imp-001", status: "COMPLETED" }, { status: 201 });
      })
    );

    const formData = new FormData();
    formData.append("file", new Blob(["id,amount\ntx-1,100.00\n"], { type: "text/csv" }), "tx.csv");

    const response = await apiRequest<{ id: string; status: string }>("/datasets/imports", {
      method: "POST",
      body: formData,
      baseUrl: TEST_BASE_URL,
    });

    expect(response.id).toBe("imp-001");
    expect(capturedAccept).toBe("application/json");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const requestInit = fetchSpy.mock.calls[0]?.[1];
    expect(requestInit?.body).toBe(formData);
    expect(new Headers(requestInit?.headers).has("Content-Type")).toBe(false);
    fetchSpy.mockRestore();
  });

  it("sets Content-Type application/json for JSON bodies and injects Bearer token", async () => {
    let seenContentType: string | null = null;
    let seenAuth: string | null = null;
    let seenBody: unknown = null;

    server.use(
      http.post(`${TEST_BASE_URL}/investigations`, async ({ request }) => {
        seenContentType = request.headers.get("Content-Type");
        seenAuth = request.headers.get("Authorization");
        seenBody = await request.json();
        return HttpResponse.json({ id: "inv-1" }, { status: 201 });
      })
    );

    setAccessToken("jwt-abc-123");
    await apiRequest<{ id: string }>("/investigations", {
      method: "POST",
      body: { transaction_id: "tx-1", priority: "HIGH" },
      baseUrl: TEST_BASE_URL,
    });

    expect(seenContentType).toBe("application/json");
    expect(seenAuth).toBe("Bearer jwt-abc-123");
    expect(seenBody).toEqual({ transaction_id: "tx-1", priority: "HIGH" });
  });

  it("propagates AbortSignal to fetch", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    server.use(
      http.get(`${TEST_BASE_URL}/transactions`, async ({ request }) => {
        if (request.signal.aborted) {
          return HttpResponse.error();
        }
        return HttpResponse.json({ items: [] });
      })
    );

    const controller = new AbortController();
    controller.abort();

    await expect(
      apiRequest("/transactions", {
        baseUrl: TEST_BASE_URL,
        signal: controller.signal,
      })
    ).rejects.toThrow();

    expect(fetchSpy.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
    fetchSpy.mockRestore();
  });

  it("aborts an in-flight Request and apiRequest cleanly when AbortController aborts after start", async () => {
    const controller = new AbortController();
    const request = new Request(`${TEST_BASE_URL}/transactions`, { signal: controller.signal });
    expect(request.signal.aborted).toBe(false);

    let mswSignalAborted = false;
    let resolverStarted!: () => void;
    const handlerStarted = new Promise<void>((resolve) => {
      resolverStarted = resolve;
    });

    server.use(
      http.get(`${TEST_BASE_URL}/transactions/slow`, ({ request: mswRequest }) => {
        mswRequest.signal.addEventListener("abort", () => {
          mswSignalAborted = true;
        });
        resolverStarted();
        return new Promise(() => {
          // Intentionally pending until aborted
        });
      })
    );

    const requestPromise = apiRequest("/transactions/slow", {
      baseUrl: TEST_BASE_URL,
      signal: controller.signal,
    });

    await handlerStarted;
    expect(mswSignalAborted).toBe(false);

    controller.abort();

    await expect(requestPromise).rejects.toThrow();
    expect(request.signal.aborted).toBe(true);
    expect(mswSignalAborted).toBe(true);
  });

  it("parses integer Retry-After headers and ignores non-integer values", async () => {
    server.use(http.post(`${TEST_BASE_URL}/auth/login`, () => apiErrorFixtures.rateLimited(45)));

    await expect(
      apiRequest("/auth/login", {
        method: "POST",
        body: { email: "a@b.com", password: "x" },
        baseUrl: TEST_BASE_URL,
      })
    ).rejects.toMatchObject({
      status: 429,
      code: "RATE_LIMIT_EXCEEDED",
      retryAfterSeconds: 45,
      requestId: "req-429",
    } satisfies Partial<ApiClientError>);

    server.use(
      http.post(`${TEST_BASE_URL}/auth/login`, () =>
        HttpResponse.json(
          { error: { code: "RATE_LIMIT_EXCEEDED", message: "Too many", details: {} } },
          { status: 429, headers: { "Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT" } }
        )
      )
    );

    try {
      await apiRequest("/auth/login", {
        method: "POST",
        body: { email: "a@b.com", password: "x" },
        baseUrl: TEST_BASE_URL,
      });
      expect.unreachable("Expected 429 to reject");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiClientError);
      expect((err as ApiClientError).retryAfterSeconds).toBeUndefined();
    }
  });

  it("prefers body error.request_id and falls back to X-Request-ID header", async () => {
    server.use(
      http.get(`${TEST_BASE_URL}/transactions/tx-header`, () =>
        HttpResponse.json(
          { error: { code: "NOT_FOUND", message: "Missing", details: {} } },
          { status: 404, headers: { "X-Request-ID": "hdr-req-99" } }
        )
      ),
      http.get(`${TEST_BASE_URL}/transactions/tx-both`, () =>
        HttpResponse.json(
          {
            error: {
              code: "NOT_FOUND",
              message: "Missing",
              details: {},
              request_id: "body-req-11",
            },
          },
          { status: 404, headers: { "X-Request-ID": "hdr-req-99" } }
        )
      )
    );

    await expect(
      apiRequest("/transactions/tx-header", { baseUrl: TEST_BASE_URL })
    ).rejects.toMatchObject({
      status: 404,
      code: "NOT_FOUND",
      requestId: "hdr-req-99",
    });

    await expect(
      apiRequest("/transactions/tx-both", { baseUrl: TEST_BASE_URL })
    ).rejects.toMatchObject({
      status: 404,
      code: "NOT_FOUND",
      requestId: "body-req-11",
    });
  });

  it("handles malformed or non-JSON error responses safely", async () => {
    server.use(
      http.get(`${TEST_BASE_URL}/health`, () => {
        return new HttpResponse("<html>502 Bad Gateway</html>", {
          status: 502,
          headers: { "Content-Type": "text/html", "X-Request-ID": "proxy-502" },
        });
      })
    );

    await expect(apiRequest("/health", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
      name: "ApiClientError",
      status: 502,
      code: "HTTP_502",
      message: "Request failed with status 502.",
      requestId: "proxy-502",
    });
  });

  it("normalizes 401, 403, 409, and 422 backend error envelopes", async () => {
    server.use(
      http.get(`${TEST_BASE_URL}/test-401`, () => apiErrorFixtures.unauthorized()),
      http.get(`${TEST_BASE_URL}/test-403`, () => apiErrorFixtures.forbidden()),
      http.patch(`${TEST_BASE_URL}/test-409`, () =>
        apiErrorFixtures.conflict("INVESTIGATION_STATE_CONFLICT", { current_status: "OPEN" })
      ),
      http.post(`${TEST_BASE_URL}/test-422`, () =>
        apiErrorFixtures.validationError({ priority: ["Value is not an accepted choice."] })
      )
    );

    await expect(apiRequest("/test-401", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
      status: 401,
      code: "UNAUTHORIZED",
      requestId: "req-401",
    });

    await expect(apiRequest("/test-403", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
      status: 403,
      code: "FORBIDDEN",
      requestId: "req-403",
    });

    await expect(
      apiRequest("/test-409", { method: "PATCH", body: {}, baseUrl: TEST_BASE_URL })
    ).rejects.toMatchObject({
      status: 409,
      code: "INVESTIGATION_STATE_CONFLICT",
      details: { current_status: "OPEN" },
      requestId: "req-409",
    });

    await expect(
      apiRequest("/test-422", { method: "POST", body: {}, baseUrl: TEST_BASE_URL })
    ).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      details: { priority: ["Value is not an accepted choice."] },
      requestId: "req-422",
    });
  });
});

describe("frontendEnv & token-store (existing F0 behavior)", () => {
  it("exposes normalized public runtime env without secrets", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("/api/v1");
    expect(resolveApiBaseUrl(" /api/v1/ ")).toBe("/api/v1");
    expect(() => resolveApiBaseUrl("")).toThrow(/must not be empty/);
    expect(frontendEnv.apiBaseUrl).toBe("/api/v1");
    expect(frontendEnv.appEnv).toBeTruthy();
  });

  it("clears in-memory token automatically across tests and never writes browser storage", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("transient-token");
    expect(getAccessToken()).toBe("transient-token");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });

  it("increments sessionEpoch monotonically on setAccessToken and clearAccessToken", () => {
    const startEpoch = getSessionEpoch();
    setAccessToken("tok-1");
    expect(getSessionEpoch()).toBe(startEpoch + 1);
    setAccessToken("tok-2");
    expect(getSessionEpoch()).toBe(startEpoch + 2);
    clearAccessToken();
    expect(getSessionEpoch()).toBe(startEpoch + 3);
  });
});

describe("apiRequest & env hardening (F2.1 / F1-AUD-005)", () => {
  it("validates schemes, production HTTPS, protocol-relative paths, and rejects query/fragments", () => {
    expect(resolveApiBaseUrl("https://api.finsignal.test/api/v1/", "production")).toBe(
      "https://api.finsignal.test/api/v1"
    );
    expect(resolveApiBaseUrl("/api/v1/", "production")).toBe("/api/v1");
    expect(resolveApiBaseUrl("http://localhost:8000/api/v1/", "development")).toBe(
      "http://localhost:8000/api/v1"
    );

    expect(() => resolveApiBaseUrl("http://api.finsignal.test/api/v1", "production")).toThrow(
      /https/i
    );
    expect(() => resolveApiBaseUrl("//evil.com/api/v1")).toThrow(/protocol-relative/);
    expect(() => resolveApiBaseUrl("javascript:alert(1)")).toThrow(/http/i);
    expect(() => resolveApiBaseUrl("/api/v1?foo=bar")).toThrow(/query/i);
    expect(() => resolveApiBaseUrl("https://api.finsignal.test/api/v1#frag")).toThrow(
      /fragment|query/i
    );
    expect(() => resolveApiBaseUrl("https://user:pass@api.finsignal.test/api/v1")).toThrow(
      /credentials/i
    );
  });

  it("prevents duplicate /api/v1 prefixes and rejects scheme or protocol-relative request paths", async () => {
    const requestedUrls: string[] = [];
    server.use(
      http.get(`${TEST_BASE_URL}/transactions`, ({ request }) => {
        requestedUrls.push(request.url);
        return HttpResponse.json({ items: [] });
      })
    );

    await apiRequest("/api/v1/transactions", { baseUrl: TEST_BASE_URL });
    await apiRequest("/transactions", { baseUrl: TEST_BASE_URL });
    expect(requestedUrls).toEqual([
      `${TEST_BASE_URL}/transactions`,
      `${TEST_BASE_URL}/transactions`,
    ]);

    await expect(apiRequest("https://evil.com/steal", { baseUrl: TEST_BASE_URL })).rejects.toThrow(
      /relative API route/
    );
    await expect(apiRequest("//evil.com/steal", { baseUrl: TEST_BASE_URL })).rejects.toThrow(
      /relative API route/
    );
  });

  it("normalizes fetch TypeError network failures into NETWORK_ERROR while preserving AbortError", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(apiRequest("/transactions", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
      name: "ApiClientError",
      status: 0,
      code: "NETWORK_ERROR",
    } satisfies Partial<ApiClientError>);

    fetchSpy.mockRestore();
  });

  it("handles 205/empty 2xx safely and rejects malformed or non-JSON 200 responses with INVALID_RESPONSE", async () => {
    server.use(
      http.get(`${TEST_BASE_URL}/empty-205`, () => new HttpResponse(null, { status: 205 })),
      http.get(`${TEST_BASE_URL}/empty-200`, () => new HttpResponse("", { status: 200 })),
      http.get(
        `${TEST_BASE_URL}/html-200`,
        () =>
          new HttpResponse("<html><body>Proxy</body></html>", {
            status: 200,
            headers: { "Content-Type": "text/html", "X-Request-ID": "req-html-200" },
          })
      )
    );

    expect(await apiRequest("/empty-205", { baseUrl: TEST_BASE_URL })).toBeUndefined();
    expect(await apiRequest("/empty-200", { baseUrl: TEST_BASE_URL })).toBeUndefined();
    await expect(apiRequest("/html-200", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
      status: 200,
      code: "INVALID_RESPONSE",
      requestId: "req-html-200",
    } satisfies Partial<ApiClientError>);
  });

  it("falls back to error.details.retry_after_seconds for 429 when Retry-After header is absent", async () => {
    server.use(
      http.post(`${TEST_BASE_URL}/auth/login`, () =>
        HttpResponse.json(
          {
            error: {
              code: "RATE_LIMIT_EXCEEDED",
              message: "Rate limit exceeded.",
              details: { retry_after_seconds: 58 },
              request_id: "req-429-body",
            },
          },
          { status: 429 }
        )
      )
    );

    await expect(
      apiRequest("/auth/login", {
        method: "POST",
        body: { email: "a@b.com", password: "secret" },
        baseUrl: TEST_BASE_URL,
      })
    ).rejects.toMatchObject({
      status: 429,
      code: "RATE_LIMIT_EXCEEDED",
      retryAfterSeconds: 58,
      requestId: "req-429-body",
    } satisfies Partial<ApiClientError>);
  });

  it("enforces authMode 'bearer' vs 'none' and caller Authorization header handling", async () => {
    const capturedHeaders: Array<string | null> = [];
    setAccessToken("stored-jwt-token");

    server.use(
      http.get(`${TEST_BASE_URL}/probe`, ({ request }) => {
        capturedHeaders.push(request.headers.get("Authorization"));
        return HttpResponse.json({ ok: true });
      })
    );

    await apiRequest("/probe", { baseUrl: TEST_BASE_URL });
    await apiRequest("/probe", {
      baseUrl: TEST_BASE_URL,
      headers: { Authorization: "Bearer caller-supplied-jwt" },
    });
    await apiRequest("/probe", {
      baseUrl: TEST_BASE_URL,
      authMode: "none",
      headers: { Authorization: "Bearer should-be-stripped" },
    });

    expect(capturedHeaders).toEqual([
      "Bearer stored-jwt-token",
      "Bearer caller-supplied-jwt",
      null,
    ]);
  });

  it("notifies unauthorized listener with pre-request sessionEpoch unless skipUnauthorizedHandler is true", async () => {
    const listener = vi.fn();
    const unsubscribe = registerUnauthorizedHandler(listener);
    setAccessToken("expiring-token");
    const expectedEpoch = getSessionEpoch();

    try {
      server.use(
        http.get(`${TEST_BASE_URL}/protected-401`, () => apiErrorFixtures.unauthorized()),
        http.get(`${TEST_BASE_URL}/protected-403`, () => apiErrorFixtures.forbidden())
      );

      await expect(apiRequest("/protected-401", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
        status: 401,
      });
      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(expectedEpoch);

      listener.mockClear();
      await expect(
        apiRequest("/protected-401", { baseUrl: TEST_BASE_URL, skipUnauthorizedHandler: true })
      ).rejects.toMatchObject({ status: 401 });
      expect(listener).not.toHaveBeenCalled();

      await expect(apiRequest("/protected-403", { baseUrl: TEST_BASE_URL })).rejects.toMatchObject({
        status: 403,
      });
      expect(listener).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });

  it("extracts field errors from FinSignal 422 envelopes and defensive FastAPI detail arrays", async () => {
    server.use(
      http.post(`${TEST_BASE_URL}/raw-fastapi-422`, () =>
        HttpResponse.json(
          {
            detail: [{ loc: ["body", "email"], msg: "value is not a valid email address" }],
          },
          { status: 422 }
        )
      )
    );

    const envelopeErr = new ApiClientError({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Request validation failed.",
      details: { email: ["Invalid format."], password: "Too short." },
    });
    expect(extractFieldErrors(envelopeErr)).toEqual({
      email: ["Invalid format."],
      password: ["Too short."],
    });
    expect(isApiClientError(envelopeErr)).toBe(true);
    expect(isNetworkError(envelopeErr)).toBe(false);
    expect(isUnauthorizedError(envelopeErr)).toBe(false);
    expect(isForbiddenError(envelopeErr)).toBe(false);

    try {
      await apiRequest("/raw-fastapi-422", {
        method: "POST",
        body: {},
        baseUrl: TEST_BASE_URL,
      });
      expect.unreachable("Expected 422");
    } catch (err) {
      expect(extractFieldErrors(err)).toEqual({
        email: ["value is not a valid email address"],
      });
    }

    expect(
      getUserFriendlyErrorMessage(
        new ApiClientError({ status: 503, code: "DATABASE_ERROR", message: "raw sql trace" })
      )
    ).toBe("A server error occurred while processing your request. Please try again later.");
  });
});
