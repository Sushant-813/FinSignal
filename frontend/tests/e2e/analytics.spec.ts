import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  signInViaUi,
} from "./helpers/auth-mock.ts";

test.describe("FinSignal Dashboard & Analytics E2E (F3.2–F3.3)", () => {
  test("verifies Dashboard Overview, URL scope updates, Analytics chart/table toggles, and zero horizontal overflow", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ANALYST" });

    await page.route("**/api/v1/analytics/overview*", async (route) => {
      const url = new URL(route.request().url());
      const ns = url.searchParams.get("source_namespace") ?? "SYNTHETIC";
      const cur = url.searchParams.get("currency") ?? "INR";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          source_namespace: ns,
          currency: cur,
          from_time: url.searchParams.get("from_time"),
          to_time: url.searchParams.get("to_time"),
          total_transaction_count: ns === "PROD_LEDGER" ? 88 : 142,
          debit_transaction_count: ns === "PROD_LEDGER" ? 60 : 108,
          credit_transaction_count: ns === "PROD_LEDGER" ? 28 : 34,
          total_volume_amount: ns === "PROD_LEDGER" ? "500000.00" : "987654.32",
          total_debit_amount: ns === "PROD_LEDGER" ? "320000.00" : "654321.10",
          total_credit_amount: ns === "PROD_LEDGER" ? "180000.00" : "333333.22",
          net_cash_flow: ns === "PROD_LEDGER" ? "-140000.00" : "-320987.88",
          average_transaction_amount: "6955.31",
          median_transaction_amount: "2450.00",
          debit_average_amount: "6058.53",
          debit_median_amount: "2100.00",
        }),
      });
    });

    await page.route("**/api/v1/analytics/trends*", async (route) => {
      const url = new URL(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          source_namespace: url.searchParams.get("source_namespace") ?? "SYNTHETIC",
          currency: url.searchParams.get("currency") ?? "INR",
          interval: url.searchParams.get("interval") ?? "day",
          timezone: url.searchParams.get("timezone") ?? "UTC",
          from_time: url.searchParams.get("from_time") ?? "2026-11-09T00:00:00Z",
          to_time: url.searchParams.get("to_time") ?? "2026-11-12T00:00:00Z",
          total_buckets: 2,
          buckets: [
            {
              bucket_start: "2026-11-10T00:00:00Z",
              transaction_count: 15,
              debit_count: 10,
              credit_count: 5,
              total_debit_amount: "24000.00",
              total_credit_amount: "11000.00",
              net_cash_flow: "-13000.00",
            },
            {
              bucket_start: "2026-11-11T00:00:00Z",
              transaction_count: 22,
              debit_count: 16,
              credit_count: 6,
              total_debit_amount: "42100.75",
              total_credit_amount: "15000.00",
              net_cash_flow: "-27100.75",
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/analytics/categories*", async (route) => {
      const url = new URL(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          source_namespace: url.searchParams.get("source_namespace") ?? "SYNTHETIC",
          currency: url.searchParams.get("currency") ?? "INR",
          direction: url.searchParams.get("direction") ?? "DEBIT",
          total_directional_amount: "100000.00",
          categories: [
            {
              category_name: "TRAVEL",
              transaction_count: 24,
              total_amount: "48500.00",
              percentage_of_total: "48.50",
              average_amount: "2020.83",
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/analytics/merchants*", async (route) => {
      const url = new URL(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          source_namespace: url.searchParams.get("source_namespace") ?? "SYNTHETIC",
          currency: url.searchParams.get("currency") ?? "INR",
          total_debit_amount: "100000.00",
          total_merchant_debit_amount: "78000.00",
          non_merchant_debit_amount: "22000.00",
          returned_merchant_count: 1,
          merchants: [
            {
              merchant_id: "11111111-1111-4111-8111-111111111111",
              merchant_name: "Apex Airlines",
              merchant_category: "TRAVEL",
              transaction_count: 11,
              total_amount: "52000.00",
              average_amount: "4727.27",
              percentage_of_total_debit: "52.00",
              percentage_of_merchant_spend: "66.67",
            },
          ],
        }),
      });
    });

    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.ANALYST.email, "valid-password");
    await expect(page.getByRole("heading", { name: "Dashboard Overview" })).toBeVisible();
    await expect(page.getByText("987,654.32")).toBeVisible();

    await page.getByLabel("Namespace").fill("PROD_LEDGER");
    await page.getByLabel("Currency (ISO)").fill("USD");
    await page.getByRole("button", { name: "Apply scope" }).click();
    await expect(page).toHaveURL(/source_namespace=PROD_LEDGER/);
    await expect(page).toHaveURL(/currency=USD/);
    await expect(page.getByText("500,000.00")).toBeVisible();

    await page.getByRole("link", { name: "Open analytics" }).click();
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.getByRole("heading", { name: "Analytics", exact: true })).toBeVisible();

    const tableButtons = page.getByRole("button", { name: "Table" });
    const count = await tableButtons.count();
    for (let i = 0; i < count; i += 1) {
      await tableButtons.nth(i).click();
    }

    await expect(page.getByText("42,100.75")).toBeVisible();
    await expect(page.getByText("48.50%")).toBeVisible();
    await expect(page.getByText("Apex Airlines")).toBeVisible();

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
      expect(hasOverflow, `Analytics overflow at ${viewport.width}x${viewport.height}`).toBe(false);
    }
  });
});
