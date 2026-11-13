import { expect, test } from "@playwright/test";
import {
  E2E_USERS,
  installMockAuthRoutes,
  isLiveE2EMode,
  signInViaUi,
} from "./helpers/auth-mock.ts";

const TX_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const INV_ID = "11111111-2222-4333-8444-555555555555";
const RELATED_TX_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const PEER_USER_ID = "00000000-0000-4000-8000-000000000099";

function buildTransactionMock() {
  return {
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
    account: {
      id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      external_account_id: "ACC-001",
    },
    latest_risk: null,
  };
}

test.describe("FinSignal Investigation Management E2E (F5.1–F5.7)", () => {
  test("Journey 1 — ANALYST creates an investigation from transaction detail and views in queue", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ANALYST" });

    let caseCreated = false;

    // Mock transaction endpoints
    await page.route("**/api/v1/transactions**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.includes(`/transactions/${TX_ID}/risk`)) {
        await route.fulfill({ status: 404 });
        return;
      }
      if (url.pathname.includes(`/transactions/${TX_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(buildTransactionMock()),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [buildTransactionMock()],
          page: 1,
          page_size: 25,
          total: 1,
          total_pages: 1,
        }),
      });
    });

    // Mock investigation endpoints
    await page.route("**/api/v1/investigations**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (
        request.method() === "POST" &&
        (url.pathname.endsWith("/investigations") || url.pathname.endsWith("/investigations/"))
      ) {
        caseCreated = true;
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: "OPEN",
            priority: "MEDIUM",
            assigned_to: null,
            assigned_user_email: null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
              category: "TRAVEL",
              payment_method: "CARD",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          }),
        });
        return;
      }

      if (request.method() === "GET" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: "OPEN",
            priority: "MEDIUM",
            assigned_to: null,
            assigned_user_email: null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
              category: "TRAVEL",
              payment_method: "CARD",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          }),
        });
        return;
      }

      if (request.method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: caseCreated
              ? [
                  {
                    id: INV_ID,
                    status: "OPEN",
                    priority: "MEDIUM",
                    assigned_to: null,
                    primary_transaction_id: TX_ID,
                    account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                    resolution: null,
                    created_at: "2026-11-13T10:00:00Z",
                    updated_at: "2026-11-13T10:00:00Z",
                  },
                ]
              : [],
            page: 1,
            page_size: 25,
            total: caseCreated ? 1 : 0,
            total_pages: caseCreated ? 1 : 0,
          }),
        });
        return;
      }

      await route.continue();
    });

    // Sign in as Analyst
    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.ANALYST.email, "valid-analyst-password-123");
    await expect(page).toHaveURL("/");

    // Navigate to Transactions via UI
    await page.getByRole("link", { name: "Transactions", exact: true }).click();
    await expect(page).toHaveURL(/\/transactions/);
    await expect(page.getByText("TXN-2026-0001")).toBeVisible();

    // Open transaction detail via UI
    await page.getByRole("link", { name: "TXN-2026-0001", exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`/transactions/${TX_ID}`));
    await expect(page.getByRole("heading", { name: "Transaction Detail" })).toBeVisible();

    // Click Investigate Transaction
    const investigateBtn = page.getByTestId("investigate-transaction-button");
    await expect(investigateBtn).toBeVisible();
    await investigateBtn.click();

    // Confirm dialog is open with prefilled transaction ID
    await expect(page.getByRole("heading", { name: "Create Investigation Case" })).toBeVisible();
    await page.getByTestId("create-investigation-submit").click();

    // Verify workspace navigation
    await expect(page).toHaveURL(`/investigations/${INV_ID}`);
    await expect(page.getByRole("heading", { name: "Investigation Case" })).toBeVisible();

    // Verify mutation controls are NOT visible for Analyst
    await expect(page.getByTestId("take-case-button")).not.toBeVisible();
    await expect(page.getByTestId("begin-review-button")).not.toBeVisible();
    await expect(page.getByTestId("resolve-case-button")).not.toBeVisible();

    // Navigate to /investigations queue via sidebar
    await page.getByRole("link", { name: "Investigations", exact: true }).click();
    await expect(page).toHaveURL("/investigations");
    await expect(page.getByTestId(`investigation-row-${INV_ID}`)).toBeVisible();
  });

  test("Journey 2 — INVESTIGATOR handles an investigation lifecycle end-to-end", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "INVESTIGATOR" });

    let currentStatus = "OPEN";
    let currentAssignee: string | null = null;
    const relatedTransactions: Record<string, unknown>[] = [];
    let resolution: string | null = null;
    let resolutionNotes: string | null = null;

    await page.route("**/api/v1/investigations**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (request.method() === "GET" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: currentStatus,
            priority: "MEDIUM",
            assigned_to: currentAssignee,
            assigned_user_email: currentAssignee ? E2E_USERS.INVESTIGATOR.email : null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
              category: "TRAVEL",
              payment_method: "CARD",
            },
            latest_risk_analysis: {
              id: "99999999-9999-4999-8999-999999999999",
              score: 0.92,
              risk_level: "CRITICAL",
              model_version: "v1.2.0",
              created_at: "2026-11-10T14:26:00Z",
            },
            related_transactions: relatedTransactions,
            resolution,
            resolution_notes: resolutionNotes,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          }),
        });
        return;
      }

      if (request.method() === "PATCH" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        const body = request.postDataJSON() as Record<string, unknown>;
        if ("assigned_to" in body) {
          currentAssignee = body.assigned_to as string | null;
        }
        if ("status" in body) {
          currentStatus = body.status as string;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: currentStatus,
            priority: "MEDIUM",
            assigned_to: currentAssignee,
            assigned_user_email: currentAssignee ? E2E_USERS.INVESTIGATOR.email : null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: relatedTransactions,
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:05:00Z",
          }),
        });
        return;
      }

      if (
        request.method() === "POST" &&
        url.pathname.includes(`/investigations/${INV_ID}/transactions`)
      ) {
        const newItem = {
          transaction_id: RELATED_TX_ID,
          relationship_type: "RELATED",
          account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          amount: "500.00",
          currency: "INR",
          direction: "CREDIT",
          occurred_at: "2026-11-10T14:30:00Z",
          created_at: "2026-11-13T10:10:00Z",
        };
        relatedTransactions.push(newItem);
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(newItem),
        });
        return;
      }

      if (
        request.method() === "POST" &&
        url.pathname.includes(`/investigations/${INV_ID}/resolve`)
      ) {
        const body = request.postDataJSON() as { resolution: string; resolution_notes: string };
        currentStatus = "RESOLVED";
        resolution = body.resolution;
        resolutionNotes = body.resolution_notes;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: "RESOLVED",
            priority: "MEDIUM",
            assigned_to: currentAssignee,
            assigned_user_email: E2E_USERS.INVESTIGATOR.email,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: relatedTransactions,
            resolution,
            resolution_notes: resolutionNotes,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:15:00Z",
          }),
        });
        return;
      }

      // Queue list endpoint
      if (request.method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: INV_ID,
                status: currentStatus,
                priority: "MEDIUM",
                assigned_to: currentAssignee,
                primary_transaction_id: TX_ID,
                account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                resolution,
                created_at: "2026-11-13T10:00:00Z",
                updated_at: "2026-11-13T10:00:00Z",
              },
            ],
            page: 1,
            page_size: 25,
            total: 1,
            total_pages: 1,
          }),
        });
        return;
      }

      await route.continue();
    });

    // 1. Sign in as Investigator
    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.INVESTIGATOR.email, "valid-investigator-password-123");

    // 2. Open Investigations from navigation
    await page.getByRole("link", { name: "Investigations", exact: true }).click();
    await expect(page).toHaveURL("/investigations");

    // 3. Click case row to open workspace
    await page.getByTestId(`investigation-row-${INV_ID}`).click();
    await expect(page).toHaveURL(`/investigations/${INV_ID}`);
    await expect(page.getByRole("heading", { name: "Investigation Case" })).toBeVisible();

    // 4. Take case (self-assignment)
    const takeCaseBtn = page.getByTestId("take-case-button");
    await expect(takeCaseBtn).toBeVisible();
    await takeCaseBtn.click();
    await expect(page.getByText(E2E_USERS.INVESTIGATOR.email)).toBeVisible();

    // 5. Begin review (OPEN -> UNDER_REVIEW)
    const beginReviewBtn = page.getByTestId("begin-review-button");
    await expect(beginReviewBtn).toBeVisible();
    await beginReviewBtn.click();
    await expect(page.getByTestId("investigation-status-badge-under_review")).toBeVisible();

    // 6. Link related transaction
    const linkBtn = page.getByTestId("open-link-transaction-button");
    await expect(linkBtn).toBeVisible();
    await linkBtn.click();
    await page.getByLabel(/Related Transaction UUID/i).fill(RELATED_TX_ID);
    await page.getByTestId("confirm-link-transaction-button").click();
    await expect(page.getByText(RELATED_TX_ID.slice(0, 8))).toBeVisible();

    // 7. Resolve case
    const resolveBtn = page.getByTestId("resolve-case-button");
    await expect(resolveBtn).toBeVisible();
    await resolveBtn.click();

    await page
      .getByLabel("Resolution Notes (Mandatory)")
      .fill("Confirmed fraud pattern based on velocity and merchant anomaly.");
    await page.getByTestId("confirm-resolve-case-button").click();

    // 8. Verify permanent read-only state & resolution banner
    await expect(page.getByTestId("investigation-resolution-banner")).toBeVisible();
    await expect(page.getByText("Case Read-Only")).toBeVisible();
    await expect(page.getByTestId("take-case-button")).not.toBeVisible();
    await expect(page.getByTestId("begin-review-button")).not.toBeVisible();
    await expect(page.getByTestId("resolve-case-button")).not.toBeVisible();
  });

  test("Journey 3 — ADMIN manages an investigation (reassign, priority update, resolve)", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "ADMIN" });

    let currentPriority = "MEDIUM";
    let currentAssignee: string | null = null;
    const currentStatus = "OPEN";

    await page.route("**/api/v1/investigations**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (request.method() === "GET" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: currentStatus,
            priority: currentPriority,
            assigned_to: currentAssignee,
            assigned_user_email: currentAssignee
              ? "delegated-investigator@finsignal.internal"
              : null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          }),
        });
        return;
      }

      if (request.method() === "PATCH" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        const body = request.postDataJSON() as Record<string, unknown>;
        if ("assigned_to" in body) {
          currentAssignee = body.assigned_to as string | null;
        }
        if ("priority" in body) {
          currentPriority = body.priority as string;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: currentStatus,
            priority: currentPriority,
            assigned_to: currentAssignee,
            assigned_user_email: currentAssignee
              ? "delegated-investigator@finsignal.internal"
              : null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:05:00Z",
          }),
        });
        return;
      }

      if (request.method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: INV_ID,
                status: currentStatus,
                priority: currentPriority,
                assigned_to: currentAssignee,
                primary_transaction_id: TX_ID,
                account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                resolution: null,
                created_at: "2026-11-13T10:00:00Z",
                updated_at: "2026-11-13T10:00:00Z",
              },
            ],
            page: 1,
            page_size: 25,
            total: 1,
            total_pages: 1,
          }),
        });
        return;
      }

      await route.continue();
    });

    await page.goto("/login");
    await signInViaUi(page, E2E_USERS.ADMIN.email, "valid-admin-password-123");

    // Open Investigations from nav
    await page.getByRole("link", { name: "Investigations", exact: true }).click();
    await expect(page).toHaveURL("/investigations");

    // Open case workspace
    await page.getByTestId(`investigation-row-${INV_ID}`).click();
    await expect(page).toHaveURL(`/investigations/${INV_ID}`);
    await expect(page.getByRole("heading", { name: "Investigation Case" })).toBeVisible();

    // 1. Admin assigns case to UUID
    const adminAssignBtn = page.getByTestId("admin-assign-button");
    await expect(adminAssignBtn).toBeVisible();
    await adminAssignBtn.click();
    await page.getByLabel(/Assignee User UUID/i).fill(PEER_USER_ID);
    await page.getByTestId("confirm-assign-button").click();
    await expect(page.getByText("delegated-investigator@finsignal.internal")).toBeVisible();

    // 2. Admin changes priority
    const priorityBtn = page.getByTestId("change-priority-button");
    await expect(priorityBtn).toBeVisible();
    await priorityBtn.click();
    const prioritySelect = page.getByRole("combobox", { name: "Priority Level" });
    await prioritySelect.click();
    await page.getByRole("option", { name: "Critical" }).click();
    await page.getByTestId("confirm-priority-button").click();
    await expect(page.getByTestId("investigation-priority-badge-critical")).toBeVisible();
  });

  test("Journey 4 — Concurrent assignment conflict displays state conflict notice and refreshes winner", async ({
    page,
  }) => {
    test.skip(isLiveE2EMode, "Mocked backend journey; skipped when E2E_API_MODE=live.");

    await installMockAuthRoutes(page, { role: "INVESTIGATOR" });

    let winningAssignee: string | null = null;

    await page.route("**/api/v1/investigations**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (request.method() === "GET" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: INV_ID,
            status: "OPEN",
            priority: "MEDIUM",
            assigned_to: winningAssignee,
            assigned_user_email: winningAssignee ? "winning-investigator@finsignal.internal" : null,
            primary_transaction: {
              id: TX_ID,
              external_transaction_id: "TXN-2026-0001",
              account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              amount: "12345.67",
              currency: "INR",
              direction: "DEBIT",
              occurred_at: "2026-11-10T14:25:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          }),
        });
        return;
      }

      if (request.method() === "PATCH" && url.pathname.includes(`/investigations/${INV_ID}`)) {
        // Simulate concurrent conflict: another investigator claimed first
        winningAssignee = PEER_USER_ID;
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "CASE_ALREADY_ASSIGNED",
              message: "Case has already been claimed by another investigator.",
            },
          }),
        });
        return;
      }

      if (request.method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: INV_ID,
                status: "OPEN",
                priority: "MEDIUM",
                assigned_to: winningAssignee,
                primary_transaction_id: TX_ID,
                account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                resolution: null,
                created_at: "2026-11-13T10:00:00Z",
                updated_at: "2026-11-13T10:00:00Z",
              },
            ],
            page: 1,
            page_size: 25,
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

    // Open Investigations from nav
    await page.getByRole("link", { name: "Investigations", exact: true }).click();
    await expect(page).toHaveURL("/investigations");

    // Open case workspace
    await page.getByTestId(`investigation-row-${INV_ID}`).click();
    await expect(page).toHaveURL(`/investigations/${INV_ID}`);

    const takeCaseBtn = page.getByTestId("take-case-button");
    await expect(takeCaseBtn).toBeVisible();
    await takeCaseBtn.click();

    // Verify conflict alert
    await expect(page.getByText("Concurrency Conflict")).toBeVisible();
    await expect(
      page.getByText("State conflict: this investigation was modified or claimed concurrently.")
    ).toBeVisible();

    // Verify winning assignee refreshed
    await expect(page.getByText("winning-investigator@finsignal.internal")).toBeVisible();
  });
});
