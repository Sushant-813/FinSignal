import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  signInViaUi,
} from "./helpers/auth-mock.ts";

const TX_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

test.describe("FinSignal Transaction Exploration & Risk E2E (F3.4–F3.7)", () => {
  test("explores filtered transactions, opens detail, runs default-ACTIVE risk scoring, and preserves return filters", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "INVESTIGATOR" });

    let hasAnalyzed = false;
    let postedAnalyzeBody: Record<string, unknown> | null = null;

    await page.route("**/api/v1/transactions?*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: TX_ID,
              source_namespace: "SYNTHETIC",
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              counterparty_account_id: null,
              merchant_id: "11111111-1111-4111-8111-111111111111",
              device_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
              location_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
              occurred_at: "2026-11-10T14:25:00Z",
              amount: "12345.67",
              currency: "INR",
              transaction_type: "CARD_PURCHASE",
              direction: "DEBIT",
              category: "TRAVEL",
              payment_method: "CARD",
              channel: "POS",
              first_seen_import_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
              created_at: "2026-11-10T14:26:00Z",
            },
          ],
          page: 1,
          page_size: 50,
          total: 1,
          total_pages: 1,
        }),
      });
    });

    await page.route(`**/api/v1/transactions/${TX_ID}/risk`, async (route) => {
      if (!hasAnalyzed) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "RISK_ANALYSIS_NOT_FOUND",
              message: "No risk evaluation exists yet.",
              details: {},
              request_id: "e2e-risk-404",
            },
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "99999999-9999-4999-8999-999999999999",
          transaction_id: TX_ID,
          model_version_id: "77777777-7777-4777-8777-777777777777",
          model_version: "iforest-v2",
          config_version: "rules-v1.4",
          feature_vector_hash: "sha256:abcdef0123456789",
          score: 78,
          risk_level: "HIGH",
          ml_anomaly_score: -0.214,
          ml_threshold: -0.1,
          normalized_ml_score: 72,
          rule_score: 65,
          normalization_params: { min_score: -0.45, max_score: 0.15 },
          factors: [
            {
              code: "NEW_DEVICE",
              label: "Unseen device fingerprint",
              severity: "HIGH",
              description: "Device DEV-88 was not observed in baseline window.",
              value_numeric: "1.00",
              value_text: "DEV-88",
              evidence: { lookback_days: 30 },
            },
          ],
          created_at: "2026-11-10T14:30:00Z",
        }),
      });
    });

    await page.route(`**/api/v1/transactions/${TX_ID}/risk/analyze`, async (route) => {
      postedAnalyzeBody = route.request().postDataJSON() as Record<string, unknown>;
      hasAnalyzed = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "99999999-9999-4999-8999-999999999999",
          transaction_id: TX_ID,
          model_version_id: "77777777-7777-4777-8777-777777777777",
          model_version: "iforest-v2",
          config_version: "rules-v1.4",
          feature_vector_hash: "sha256:abcdef0123456789",
          score: 78,
          risk_level: "HIGH",
          ml_anomaly_score: -0.214,
          ml_threshold: -0.1,
          normalized_ml_score: 72,
          rule_score: 65,
          normalization_params: { min_score: -0.45, max_score: 0.15 },
          factors: [
            {
              code: "NEW_DEVICE",
              label: "Unseen device fingerprint",
              severity: "HIGH",
              description: "Device DEV-88 was not observed in baseline window.",
              value_numeric: "1.00",
              value_text: "DEV-88",
              evidence: { lookback_days: 30 },
            },
          ],
          created_at: "2026-11-10T14:30:00Z",
        }),
      });
    });

    await page.route(`**/api/v1/transactions/${TX_ID}?*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: TX_ID,
          source_namespace: "SYNTHETIC",
          external_transaction_id: "TXN-2026-0001",
          first_seen_import_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
          account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          counterparty_account_id: null,
          merchant_id: "11111111-1111-4111-8111-111111111111",
          device_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
          location_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
          occurred_at: "2026-11-10T14:25:00Z",
          amount: "12345.67",
          currency: "INR",
          transaction_type: "CARD_PURCHASE",
          direction: "DEBIT",
          category: "TRAVEL",
          payment_method: "CARD",
          channel: "POS",
          created_at: "2026-11-10T14:26:00Z",
          account: {
            id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            external_account_id: "ACC-1001",
            account_type: "CHECKING",
            status: "ACTIVE",
          },
          counterparty_account: null,
          merchant: {
            id: "11111111-1111-4111-8111-111111111111",
            external_merchant_id: "MER-101",
            merchant_name: "Apex Airlines",
            merchant_category: "TRAVEL",
          },
          device: {
            id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            external_device_id: "DEV-88",
            device_type: "MOBILE_IOS",
          },
          location: {
            id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            city: "Bengaluru",
            state: "KA",
            country: "IN",
          },
          latest_risk: null,
        }),
      });
    });

    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.INVESTIGATOR.email, "valid-password");
    await expect(page.getByRole("heading", { name: "Dashboard Overview" })).toBeVisible();

    await page.getByRole("link", { name: "Transactions", exact: true }).click();
    await expect(page).toHaveURL(/\/transactions/);
    await expect(page.getByText("TXN-2026-0001")).toBeVisible();
    await expect(page.getByText("12,345.67")).toBeVisible();

    await page.getByRole("button", { name: /Amount/i }).click();
    await expect(page).toHaveURL(/sort_by=amount/);

    await page.getByRole("link", { name: "TXN-2026-0001", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/transactions/${TX_ID}`));
    await expect(page.getByRole("heading", { name: "Immutable Transaction Facts" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Relational Entity Context" })).toBeVisible();
    await expect(page.getByText("No risk analysis recorded yet.")).toBeVisible();

    await page.getByRole("button", { name: "Run risk analysis" }).click();
    await expect(page.getByText("HIGH RISK")).toBeVisible();
    await expect(page.getByText("Unseen device fingerprint")).toBeVisible();
    await expect(page.getByText(/not an automated fraud verdict/i)).toBeVisible();
    expect(postedAnalyzeBody).toEqual({});

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
      expect(
        hasOverflow,
        `Transaction detail overflow at ${viewport.width}x${viewport.height}`
      ).toBe(false);
    }

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.getByRole("link", { name: /Back to Transactions/i }).click();
    await expect(page).toHaveURL(/\/transactions.*sort_by=amount/);
  });
});
