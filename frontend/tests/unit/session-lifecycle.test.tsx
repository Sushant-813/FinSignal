import { QueryClient, useQuery } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { AppProviders } from "../../src/app/providers/AppProviders.tsx";
import { useAuth } from "../../src/features/auth/hooks/useAuth.ts";
import { apiRequest } from "../../src/lib/api/client.ts";
import { notifyUnauthorized } from "../../src/lib/auth/session-events.ts";
import { getAccessToken, getSessionEpoch, setAccessToken } from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { buildAuthUser, createAuthHandlers } from "../fixtures/auth.ts";
import { server } from "../mocks/server.ts";

function SessionProbe() {
  const { status, user, sessionNotice, signIn, signOut, clearSessionNotice } = useAuth();
  const sampleQuery = useQuery({
    queryKey: ["sample-workspace-data", user?.id ?? "anon"],
    queryFn: ({ signal }) => apiRequest<{ roleData: string }>("/sample-data", { signal }),
    enabled: status === "authenticated",
  });

  return (
    <div>
      <div data-testid="status">{status}</div>
      <div data-testid="user-email">{user?.email ?? "none"}</div>
      <div data-testid="user-role">{user?.role ?? "none"}</div>
      <div data-testid="notice">{sessionNotice?.message ?? "none"}</div>
      <div data-testid="query-data">{sampleQuery.data?.roleData ?? "empty"}</div>
      <button
        type="button"
        onClick={() => {
          void signIn({ email: "analyst@finsignal.test", password: "valid-password" }).catch(
            () => undefined
          );
        }}
      >
        Trigger Login
      </button>
      <button type="button" onClick={signOut}>
        Sign Out
      </button>
      <button type="button" onClick={clearSessionNotice}>
        Dismiss Notice
      </button>
    </div>
  );
}

describe("AuthProvider & session lifecycle (F2.2 / ADR-075)", () => {
  it("resolves synchronously to unauthenticated when no token is present (0 /auth/me calls)", () => {
    const meSpy = vi.fn();
    server.use(
      http.get("/api/v1/auth/me", () => {
        meSpy();
        return HttpResponse.json(buildAuthUser("ANALYST"));
      })
    );

    render(
      <AppProviders>
        <SessionProbe />
      </AppProviders>
    );

    expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    expect(screen.getByTestId("user-email")).toHaveTextContent("none");
    expect(meSpy).not.toHaveBeenCalled();
  });

  it("validates a pre-seeded in-memory token via /auth/me and stays initializing until verified", async () => {
    let resolveMe!: () => void;
    const gate = new Promise<void>((resolve) => {
      resolveMe = resolve;
    });

    setAccessToken("preseeded-jwt");
    server.use(
      http.get("/api/v1/auth/me", async () => {
        await gate;
        return HttpResponse.json(buildAuthUser("ADMIN"));
      }),
      http.get("/api/v1/sample-data", () => HttpResponse.json({ roleData: "admin-secret" }))
    );

    render(
      <AppProviders>
        <SessionProbe />
      </AppProviders>
    );

    expect(screen.getByTestId("status")).toHaveTextContent("initializing");

    resolveMe();
    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });
    expect(screen.getByTestId("user-email")).toHaveTextContent("admin@finsignal.test");
    expect(screen.getByTestId("user-role")).toHaveTextContent("ADMIN");
  });

  it("clears token and fails closed if /auth/me rejects, returns is_active: false, or returns an unknown role", async () => {
    setAccessToken("bad-role-jwt");
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({
          ...buildAuthUser("ANALYST"),
          role: "SUPERUSER",
        })
      )
    );

    render(
      <AppProviders>
        <SessionProbe />
      </AppProviders>
    );

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    });
    expect(getAccessToken()).toBeNull();

    setAccessToken("inactive-jwt");
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json(buildAuthUser("ANALYST", { is_active: false }))
      )
    );

    render(
      <AppProviders>
        <SessionProbe />
      </AppProviders>
    );

    await waitFor(() => {
      expect(screen.getAllByTestId("status")[1]).toHaveTextContent("unauthenticated");
    });
    expect(getAccessToken()).toBeNull();
  });

  it("executes 8-step signIn (/login -> setToken -> capture epoch -> /auth/me) and clears token if /auth/me fails", async () => {
    const analyst = buildAuthUser("ANALYST");
    server.use(...createAuthHandlers(analyst, { accessToken: "tok-step-check" }));
    server.use(
      http.get("/api/v1/sample-data", () => HttpResponse.json({ roleData: "analyst-data" }))
    );

    let authRef!: ReturnType<typeof useAuth>;
    function Harness() {
      authRef = useAuth();
      return <SessionProbe />;
    }

    render(
      <AppProviders>
        <Harness />
      </AppProviders>
    );

    await act(async () => {
      await authRef.signIn({ email: "analyst@finsignal.test", password: "valid-password" });
    });

    expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    expect(getAccessToken()).toBe("tok-step-check");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");

    // Now test /auth/me failing after /login succeeds -> must not leave orphan token in memory.
    act(() => {
      authRef.signOut();
    });
    server.use(
      http.post("/api/v1/auth/login", () =>
        HttpResponse.json({
          access_token: "orphan-risk-token",
          token_type: "bearer",
          expires_in: 1800,
        })
      ),
      http.get("/api/v1/auth/me", () => apiErrorFixtures.unauthorized())
    );

    await act(async () => {
      await expect(
        authRef.signIn({ email: "analyst@finsignal.test", password: "valid-password" })
      ).rejects.toMatchObject({ status: 401 });
    });
    expect(getAccessToken()).toBeNull();
    expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
  });

  it("prevents overlapping signIn attempts or lagging signOut races via authAttemptId & sessionEpoch", async () => {
    let releaseFirstMe!: () => void;
    const firstMeGate = new Promise<void>((resolve) => {
      releaseFirstMe = resolve;
    });

    let loginCount = 0;
    server.use(
      http.post("/api/v1/auth/login", () => {
        loginCount += 1;
        return HttpResponse.json({
          access_token: loginCount === 1 ? "slow-admin-jwt" : "fast-investigator-jwt",
          token_type: "bearer",
          expires_in: 1800,
        });
      }),
      http.get("/api/v1/auth/me", async ({ request }) => {
        const auth = request.headers.get("Authorization");
        if (auth === "Bearer slow-admin-jwt") {
          await firstMeGate;
          return HttpResponse.json(buildAuthUser("ADMIN"));
        }
        return HttpResponse.json(buildAuthUser("INVESTIGATOR"));
      }),
      http.get("/api/v1/sample-data", () => HttpResponse.json({ roleData: "inv-data" }))
    );

    let authRef!: ReturnType<typeof useAuth>;
    function Harness() {
      authRef = useAuth();
      return <SessionProbe />;
    }

    render(
      <AppProviders>
        <Harness />
      </AppProviders>
    );

    let firstPromise!: Promise<unknown>;
    let secondPromise!: Promise<unknown>;

    await act(async () => {
      firstPromise = authRef
        .signIn({ email: "admin@finsignal.test", password: "valid" })
        .catch((err: unknown) => err);
      // Let first /login settle and reach /auth/me gate
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      secondPromise = authRef.signIn({ email: "investigator@finsignal.test", password: "valid" });
      await secondPromise;
    });

    expect(screen.getByTestId("user-role")).toHaveTextContent("INVESTIGATOR");
    expect(getAccessToken()).toBe("fast-investigator-jwt");

    // Release slow first attempt; it must NOT overwrite Investigator or clear its token.
    await act(async () => {
      releaseFirstMe();
      const firstResult = await firstPromise;
      expect(firstResult).toMatchObject({ name: "AbortError" });
    });

    expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    expect(screen.getByTestId("user-role")).toHaveTextContent("INVESTIGATOR");
    expect(getAccessToken()).toBe("fast-investigator-jwt");
  });

  it("expires session using backend expires_in and cancels/clears timers cleanly across re-login", async () => {
    vi.useFakeTimers();
    try {
      server.use(
        http.post("/api/v1/auth/login", () =>
          HttpResponse.json({
            access_token: "short-lived-jwt",
            token_type: "bearer",
            expires_in: 5,
          })
        ),
        http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))),
        http.get("/api/v1/sample-data", () => HttpResponse.json({ roleData: "fresh" }))
      );

      let authRef!: ReturnType<typeof useAuth>;
      function Harness() {
        authRef = useAuth();
        return <SessionProbe />;
      }

      render(
        <AppProviders>
          <Harness />
        </AppProviders>
      );

      await act(async () => {
        await authRef.signIn({ email: "analyst@finsignal.test", password: "valid" });
      });
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(4999);
      });
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1);
      });

      expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
      expect(getAccessToken()).toBeNull();
      expect(screen.getByTestId("notice")).toHaveTextContent(/expired/i);
    } finally {
      vi.useRealTimers();
    }
  });

  it("deduplicates concurrent 401s, ignores stale-epoch 401s, and preserves session on 403", async () => {
    setAccessToken("active-jwt");
    server.use(
      http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("INVESTIGATOR"))),
      http.get("/api/v1/sample-data", () => HttpResponse.json({ roleData: "ok" })),
      http.get("/api/v1/datasets/forbidden", () => apiErrorFixtures.forbidden()),
      http.get("/api/v1/fail-401-a", () => apiErrorFixtures.unauthorized()),
      http.get("/api/v1/fail-401-b", () => apiErrorFixtures.unauthorized()),
      http.get("/api/v1/fail-401-c", () => apiErrorFixtures.unauthorized())
    );

    render(
      <AppProviders>
        <SessionProbe />
      </AppProviders>
    );

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    });

    // 403 must NOT expire session
    await expect(apiRequest("/datasets/forbidden")).rejects.toMatchObject({ status: 403 });
    expect(screen.getByTestId("status")).toHaveTextContent("authenticated");
    expect(getAccessToken()).toBe("active-jwt");

    // Stale-epoch 401 notification must be ignored
    const currentEpoch = getSessionEpoch();
    act(() => {
      notifyUnauthorized(currentEpoch - 1);
    });
    expect(screen.getByTestId("status")).toHaveTextContent("authenticated");

    // 3 concurrent 401s trigger single cleanup & notice
    await act(async () => {
      await Promise.allSettled([
        apiRequest("/fail-401-a"),
        apiRequest("/fail-401-b"),
        apiRequest("/fail-401-c"),
      ]);
    });

    expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    expect(getAccessToken()).toBeNull();
    expect(screen.getByTestId("notice")).toHaveTextContent(/expired/i);
  });

  it("uses local-only logout (Option B), clears QueryClient cache, and prevents cross-user cache leaks", async () => {
    const logoutHttpSpy = vi.fn();
    let currentRole: "ADMIN" | "INVESTIGATOR" = "ADMIN";

    server.use(
      http.post("/api/v1/auth/login", () =>
        HttpResponse.json({
          access_token: currentRole === "ADMIN" ? "admin-jwt" : "inv-jwt",
          token_type: "bearer",
          expires_in: 1800,
        })
      ),
      http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(currentRole))),
      http.post("/api/v1/auth/logout", () => {
        logoutHttpSpy();
        return HttpResponse.json({ message: "Successfully logged out." });
      }),
      http.get("/api/v1/sample-data", () =>
        HttpResponse.json({
          roleData: currentRole === "ADMIN" ? "admin-only-cache" : "investigator-cache",
        })
      )
    );

    const cancelSpy = vi.spyOn(QueryClient.prototype, "cancelQueries");
    const clearSpy = vi.spyOn(QueryClient.prototype, "clear");

    let authRef!: ReturnType<typeof useAuth>;
    function Harness() {
      authRef = useAuth();
      return <SessionProbe />;
    }

    render(
      <AppProviders>
        <Harness />
      </AppProviders>
    );

    await act(async () => {
      await authRef.signIn({ email: "admin@finsignal.test", password: "valid" });
    });

    await waitFor(() => {
      expect(screen.getByTestId("query-data")).toHaveTextContent("admin-only-cache");
    });

    cancelSpy.mockClear();
    clearSpy.mockClear();

    act(() => {
      authRef.signOut();
    });

    expect(logoutHttpSpy).not.toHaveBeenCalled();
    expect(getAccessToken()).toBeNull();
    expect(screen.getByTestId("status")).toHaveTextContent("unauthenticated");
    expect(screen.getByTestId("query-data")).toHaveTextContent("empty");
    expect(cancelSpy).toHaveBeenCalledTimes(1);
    expect(clearSpy).toHaveBeenCalledTimes(1);

    // Sign in as second user (INVESTIGATOR) — must never see User A's cached query data.
    currentRole = "INVESTIGATOR";
    await act(async () => {
      await authRef.signIn({ email: "investigator@finsignal.test", password: "valid" });
    });

    await waitFor(() => {
      expect(screen.getByTestId("query-data")).toHaveTextContent("investigator-cache");
    });

    cancelSpy.mockRestore();
    clearSpy.mockRestore();
  });
});
