import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  signInViaUi,
} from "./helpers/auth-mock.ts";

test.describe("FinSignal Application Shell & Role Navigation E2E (F2.6)", () => {
  test("verifies ADMIN navigation, keyboard sign-out, and responsive viewports with zero horizontal overflow", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ADMIN" });
    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.ADMIN.email, "valid-password");
    await expect(page.getByRole("heading", { name: "Workspace Overview" })).toBeVisible();

    // Responsive overflow check at desktop, tablet, and mobile viewports
    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 1024, height: 768 },
      { width: 768, height: 1024 },
      { width: 360, height: 800 },
    ]) {
      await page.setViewportSize(viewport);
      const hasOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth
      );
      expect(hasOverflow, `Overflow detected at ${viewport.width}x${viewport.height}`).toBe(false);
    }

    // Mobile drawer open + Escape close on 360x800
    await page.setViewportSize({ width: 360, height: 800 });
    await page.getByRole("button", { name: "Open navigation menu" }).click();
    await expect(page.getByRole("dialog", { name: "Primary navigation" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Primary navigation" })).toBeHidden();

    // Desktop navigation & Dataset management capability display
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.getByRole("link", { name: "Datasets" }).click();
    await expect(page).toHaveURL(/\/datasets$/);
    await expect(page.getByRole("heading", { name: "Datasets" })).toBeVisible();
    await expect(page.getByText(/full dataset permissions/i)).toBeVisible();

    // Supported routes only — no uncontracted nav items
    await expect(page.getByRole("link", { name: /Accounts/i })).toHaveCount(0);
    await expect(page.getByRole("link", { name: /Audit/i })).toHaveCount(0);

    // Sign out clears session and returns to login
    await page.getByRole("button", { name: new RegExp(E2E_USERS.ADMIN.email, "i") }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("verifies INVESTIGATOR read-only dataset navigation vs disabled upload/recovery policy", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "INVESTIGATOR" });
    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.INVESTIGATOR.email, "valid-password");
    await expect(page.getByRole("heading", { name: "Workspace Overview" })).toBeVisible();
    await expect(page.getByText("Not available for Investigator")).toBeVisible();

    await page.getByRole("link", { name: "Datasets" }).click();
    await expect(page).toHaveURL(/\/datasets$/);
    await expect(
      page.getByText(/Read-only dataset import history is permitted for Investigator accounts/i)
    ).toBeVisible();
  });
});
