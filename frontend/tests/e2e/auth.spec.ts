import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  readE2EEnv,
  signInViaUi,
} from "./helpers/auth-mock.ts";

test.describe("FinSignal Authentication E2E (F2.6 / ADR-075)", () => {
  test("redirects unauthenticated access to /login, restores safe redirect target, requires re-login after reload, and keeps storage empty", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ANALYST", expectedPassword: "valid-password" });

    await page.goto("/investigations?status=OPEN");
    await expect(page).toHaveURL(/\/login\?redirect=%2Finvestigations%3Fstatus%3DOPEN/);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

    // Failed login shows safe error without navigating
    await signInViaUi(page, E2E_USERS.ANALYST.email, "wrong-password");
    await expect(page.getByRole("alert")).toContainText(/Invalid email or password/i);
    await expect(page).toHaveURL(/\/login/);

    // Successful login restores safe redirect target
    await signInViaUi(page, E2E_USERS.ANALYST.email, "valid-password");
    await expect(page).toHaveURL(/\/investigations\?status=OPEN$/);
    await expect(page.getByRole("heading", { name: "Investigations" })).toBeVisible();

    // ADR-075: zero tokens in browser storage, cookies, or URL
    const storageState = await page.evaluate(() => ({
      localLength: window.localStorage.length,
      sessionLength: window.sessionStorage.length,
      cookie: document.cookie,
      href: window.location.href,
    }));
    expect(storageState.localLength).toBe(0);
    expect(storageState.sessionLength).toBe(0);
    expect(storageState.cookie).toBe("");
    expect(storageState.href).not.toContain("e2e-synthetic-jwt");

    // ADR-075: full page reload clears in-memory session and requires re-login
    await page.reload();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("neutralizes unsafe external redirect targets and surfaces 429 rate-limit feedback", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    let attempts = 0;
    await page.route("**/api/v1/auth/login", async (route) => {
      attempts += 1;
      if (attempts === 1) {
        await route.fulfill({
          status: 429,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "RATE_LIMIT_EXCEEDED",
              message: "Rate limit exceeded.",
              details: { retry_after_seconds: 35 },
              request_id: "e2e-req-429",
            },
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "e2e-admin-jwt",
          token_type: "bearer",
          expires_in: 1800,
        }),
      });
    });

    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(E2E_USERS.ADMIN),
      });
    });

    await page.goto("/login?redirect=https%3A%2F%2Fevil.example%2Fphish");
    await signInViaUi(page, E2E_USERS.ADMIN.email, "valid-password");
    await expect(page.getByRole("alert")).toContainText(/wait 35 seconds/i);

    await signInViaUi(page, E2E_USERS.ADMIN.email, "valid-password");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "Workspace Overview" })).toBeVisible();
  });

  test("expires session automatically after backend expires_in and returns to login with notice", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ANALYST", expiresIn: 1 });
    await page.goto("/login");

    await signInViaUi(page, E2E_USERS.ANALYST.email, "valid-password");
    await expect(page.getByRole("heading", { name: "Workspace Overview" })).toBeVisible();

    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
    await expect(page.getByRole("status")).toContainText(/session has expired/i);
  });
});

if (isLiveE2EMode) {
  test.describe("FinSignal Live Backend Authentication E2E", () => {
    test("live backend smoke login (E2E_API_MODE=live with env credentials)", async ({ page }) => {
      const email = readE2EEnv("E2E_LIVE_EMAIL");
      const password = readE2EEnv("E2E_LIVE_PASSWORD");
      test.skip(!email || !password, "Set E2E_LIVE_EMAIL and E2E_LIVE_PASSWORD for live E2E.");

      await page.goto("/login");
      await signInViaUi(page, email ?? "", password ?? "");
      await expect(page).toHaveURL(/\/$/);
      await expect(page.getByRole("heading", { name: "Workspace Overview" })).toBeVisible();
    });
  });
}
