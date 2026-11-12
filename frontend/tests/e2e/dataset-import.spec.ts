import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  signInViaUi,
} from "./helpers/auth-mock.ts";

const IMPORT_ID = "imp-9b7e3f2a-1122-3344-5566-778899aabbcc";
const SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

test.describe("FinSignal Dataset Import & Ingestion Visibility E2E (F4.1–F4.6)", () => {
  test("ANALYST uploads dataset CSV, inspects ledger, views import detail, and recovers failed import", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ANALYST" });

    let currentImportStatus = "FAILED";

    await page.route("**/api/v1/datasets/imports**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (request.method() === "GET" && (url.pathname.endsWith("/datasets/imports") || url.pathname.endsWith("/datasets/imports/"))) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: IMPORT_ID,
                source_namespace: "SYNTHETIC",
                source_type: "SYNTHETIC",
                filename: "november_transactions.csv",
                file_hash: SHA256,
                total_rows: 1000,
                valid_rows: 990,
                invalid_rows: 10,
                status: currentImportStatus,
                started_at: "2026-11-12T10:00:00Z",
                completed_at: currentImportStatus === "COMPLETED" ? "2026-11-12T10:00:20Z" : null,
                is_duplicate: false,
              },
            ],
            page: 1,
            page_size: 20,
            total: 1,
            total_pages: 1,
          }),
        });
        return;
      }

      if (request.method() === "GET" && url.pathname.includes(`/datasets/imports/${IMPORT_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: IMPORT_ID,
            source_namespace: "SYNTHETIC",
            source_type: "SYNTHETIC",
            filename: "november_transactions.csv",
            file_hash: SHA256,
            total_rows: 1000,
            valid_rows: 990,
            invalid_rows: 10,
            status: currentImportStatus,
            started_at: "2026-11-12T10:00:00Z",
            completed_at: currentImportStatus === "COMPLETED" ? "2026-11-12T10:00:20Z" : null,
            is_duplicate: false,
            errors: [
              {
                row_number: 14,
                field_name: "amount",
                error_code: "INVALID_DECIMAL",
                message: "Amount could not be parsed to canonical monetary decimal.",
              },
            ],
          }),
        });
        return;
      }

      if (request.method() === "POST" && url.pathname.endsWith(`/datasets/imports/${IMPORT_ID}/recover`)) {
        currentImportStatus = "COMPLETED";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: IMPORT_ID,
            source_namespace: "SYNTHETIC",
            source_type: "SYNTHETIC",
            filename: "november_transactions.csv",
            file_hash: SHA256,
            total_rows: 1000,
            valid_rows: 1000,
            invalid_rows: 0,
            status: "COMPLETED",
            started_at: "2026-11-12T10:00:00Z",
            completed_at: "2026-11-12T10:01:00Z",
            is_duplicate: false,
          }),
        });
        return;
      }

      if (request.method() === "POST" && url.pathname.endsWith("/datasets/imports")) {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: IMPORT_ID,
            source_namespace: "SYNTHETIC",
            source_type: "SYNTHETIC",
            filename: "new_upload.csv",
            file_hash: SHA256,
            total_rows: 50,
            valid_rows: 50,
            invalid_rows: 0,
            status: "COMPLETED",
            started_at: "2026-11-12T10:05:00Z",
            completed_at: "2026-11-12T10:05:05Z",
            is_duplicate: false,
          }),
        });
        return;
      }

      await route.continue();
    });

    // 1. Navigate to /login and Sign in as Analyst
    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.ANALYST.email, "valid-analyst-password-123");
    await expect(page).toHaveURL("/");

    // 2. Navigate to /datasets
    await page.getByRole("link", { name: "Datasets" }).click();
    await expect(page).toHaveURL("/datasets");
    await expect(page.getByRole("heading", { name: "Datasets" })).toBeVisible();

    // 3. Verify upload card is present for Analyst
    await expect(page.getByRole("heading", { name: "Import Transaction Dataset" })).toBeVisible();

    // 4. Inspect ledger row
    await expect(page.getByText("november_transactions.csv")).toBeVisible();
    await expect(page.getByText("Failed")).toBeVisible();

    // 5. Open Import Details
    await page.getByRole("link", { name: /View details for dataset import/i }).click();
    await expect(page).toHaveURL(`/datasets/imports/${IMPORT_ID}`);
    await expect(page.getByRole("heading", { name: "Import Details" })).toBeVisible();

    // 6. Verify fact card and quarantine error row
    await expect(page.getByText("INVALID_DECIMAL")).toBeVisible();
    await expect(page.getByText("Amount could not be parsed to canonical monetary decimal.")).toBeVisible();

    // 7. Click Recover Import and submit file
    const recoverBtn = page.getByRole("button", { name: /Recover Import/i });
    await expect(recoverBtn).toBeVisible();
    await recoverBtn.click();

    await expect(page.getByRole("heading", { name: "Recover Failed Dataset Import" })).toBeVisible();

    // Upload matching CSV file in modal
    const nodeBuffer = (globalThis as { Buffer?: { from: (str: string, enc?: string) => unknown } }).Buffer;
    const fileBuffer = nodeBuffer
      ? (nodeBuffer.from("account_id,amount\nacc1,100.00\n", "utf-8") as unknown as Uint8Array)
      : new TextEncoder().encode("account_id,amount\nacc1,100.00\n");

    await page.locator("#recovery-file-input").setInputFiles({
      name: "november_transactions.csv",
      mimeType: "text/csv",
      buffer: fileBuffer,
    });

    await page.getByRole("button", { name: "Resume Ingestion" }).click();

    // 8. Assert successful recovery transitions
    await expect(page.getByText("Completed", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /Recover Import/i })).not.toBeVisible();
  });

  test("INVESTIGATOR has read-only access: upload card and recovery action are hidden", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "INVESTIGATOR" });

    await page.route("**/api/v1/datasets/imports*", async (route) => {
      const request = route.request();
      if (request.method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: IMPORT_ID,
                source_namespace: "SYNTHETIC",
                source_type: "SYNTHETIC",
                filename: "investigator_view.csv",
                file_hash: SHA256,
                total_rows: 100,
                valid_rows: 95,
                invalid_rows: 5,
                status: "FAILED",
                started_at: "2026-11-12T10:00:00Z",
                completed_at: null,
                is_duplicate: false,
              },
            ],
            page: 1,
            page_size: 20,
            total: 1,
            total_pages: 1,
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.INVESTIGATOR.email, "valid-investigator-password-123");
    await page.getByRole("link", { name: "Datasets" }).click();
    await expect(page).toHaveURL("/datasets");

    // Read-only banner is displayed
    await expect(page.getByLabel("Investigator read-only dataset permissions")).toBeVisible();

    // Upload Card is strictly hidden
    await expect(page.getByRole("heading", { name: "Import Transaction Dataset" })).not.toBeVisible();
  });
});
