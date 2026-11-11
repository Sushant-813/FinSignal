import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { ApiClientError, apiRequest } from "../../src/lib/api/client.ts";
import { frontendEnv, resolveApiBaseUrl } from "../../src/lib/api/env.ts";
import {
  clearAccessToken,
  getAccessToken,
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
});
