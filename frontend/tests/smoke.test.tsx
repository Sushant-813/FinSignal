import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import App from "../src/App.tsx";
import type { components } from "../src/api/generated/schema.ts";
import { ApiClientError, apiRequest } from "../src/lib/api/client.ts";
import { resolveApiBaseUrl } from "../src/lib/api/env.ts";
import { clearAccessToken, getAccessToken, setAccessToken } from "../src/lib/auth/token-store.ts";

type TransactionListResponse = components["schemas"]["TransactionListResponse"];

const server = setupServer(
  http.get("http://localhost/api/v1/transactions", ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (auth !== "Bearer test-jwt-token") {
      return HttpResponse.json(
        {
          error: {
            code: "UNAUTHORIZED",
            message: "Authentication credentials were not provided or are invalid.",
            details: {},
            request_id: "req-unauth",
          },
        },
        { status: 401 }
      );
    }

    const payload: TransactionListResponse = {
      items: [],
      page: 1,
      page_size: 50,
      total: 0,
      total_pages: 0,
    };
    return HttpResponse.json(payload);
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  clearAccessToken();
});
afterAll(() => server.close());

describe("Phase F0 frontend readiness baseline", () => {
  it("renders baseline FinSignal readiness shell", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "FinSignal" })).toBeInTheDocument();
    expect(screen.getByText(/Phase F0 readiness baseline/i)).toBeInTheDocument();
  });

  it("normalizes VITE_API_BASE_URL safely", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("/api/v1");
    expect(resolveApiBaseUrl("http://localhost:8000/api/v1/")).toBe("http://localhost:8000/api/v1");
    expect(() => resolveApiBaseUrl("   ")).toThrow(/must not be empty/);
  });

  it("holds access tokens strictly in memory without browser persistence", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("mem-token-123");
    expect(getAccessToken()).toBe("mem-token-123");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });

  it("injects Bearer token and parses generated OpenAPI response + error envelopes via MSW", async () => {
    await expect(
      apiRequest<TransactionListResponse>("/transactions", {
        baseUrl: "http://localhost/api/v1",
      })
    ).rejects.toMatchObject({
      name: "ApiClientError",
      status: 401,
      code: "UNAUTHORIZED",
      requestId: "req-unauth",
    } satisfies Partial<ApiClientError>);

    setAccessToken("test-jwt-token");
    const data = await apiRequest<TransactionListResponse>("/transactions", {
      baseUrl: "http://localhost/api/v1",
    });
    expect(data.total).toBe(0);
    expect(data.page_size).toBe(50);
  });
});
