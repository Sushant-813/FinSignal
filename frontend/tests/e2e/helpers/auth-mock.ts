import type { Page } from "@playwright/test";

export type E2ERole = "ADMIN" | "ANALYST" | "INVESTIGATOR";

export interface E2EUser {
  id: string;
  email: string;
  role: E2ERole;
  is_active: boolean;
  created_at: string;
}

export const E2E_USERS: Record<E2ERole, E2EUser> = {
  ADMIN: {
    id: "00000000-0000-4000-8000-000000000001",
    email: "admin@finsignal.test",
    role: "ADMIN",
    is_active: true,
    created_at: "2026-11-10T10:00:00Z",
  },
  ANALYST: {
    id: "00000000-0000-4000-8000-000000000002",
    email: "analyst@finsignal.test",
    role: "ANALYST",
    is_active: true,
    created_at: "2026-11-10T10:00:00Z",
  },
  INVESTIGATOR: {
    id: "00000000-0000-4000-8000-000000000003",
    email: "investigator@finsignal.test",
    role: "INVESTIGATOR",
    is_active: true,
    created_at: "2026-11-10T10:00:00Z",
  },
};

export interface MockAuthOptions {
  role?: E2ERole;
  expiresIn?: number;
  expectedPassword?: string;
}

export function readE2EEnv(name: string): string | undefined {
  const nodeProcess = (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process;
  return nodeProcess?.env?.[name];
}

export const isLiveE2EMode = readE2EEnv("E2E_API_MODE") === "live";

export async function installMockAuthRoutes(page: Page, options: MockAuthOptions = {}) {
  if (isLiveE2EMode) {
    return;
  }

  const role = options.role ?? "ANALYST";
  const user = E2E_USERS[role];
  const token = `e2e-synthetic-jwt-${role.toLowerCase()}`;
  const expiresIn = options.expiresIn ?? 1800;

  await page.route("**/api/v1/auth/login", async (route) => {
    const body = route.request().postDataJSON() as { email?: string; password?: string } | null;
    if (options.expectedPassword && body?.password !== options.expectedPassword) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "UNAUTHORIZED",
            message: "Invalid email or password.",
            details: {},
            request_id: "e2e-req-401",
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: token,
        token_type: "bearer",
        expires_in: expiresIn,
      }),
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    const authHeader = route.request().headers().authorization;
    if (authHeader !== `Bearer ${token}`) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "UNAUTHORIZED",
            message: "Invalid session token.",
            details: {},
            request_id: "e2e-req-me-401",
          },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(user),
    });
  });

  await page.route("**/api/v1/analytics/overview*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        source_namespace: "SYNTHETIC",
        currency: "INR",
        from_time: "2026-10-12T00:00:00Z",
        to_time: "2026-11-12T00:00:00Z",
        total_transaction_count: 142,
        debit_transaction_count: 108,
        credit_transaction_count: 34,
        total_volume_amount: "987654.32",
        total_debit_amount: "654321.10",
        total_credit_amount: "333333.22",
        net_cash_flow: "-320987.88",
        average_transaction_amount: "6955.31",
        median_transaction_amount: "2450.00",
        debit_average_amount: "6058.53",
        debit_median_amount: "2100.00",
      }),
    });
  });
}

export async function signInViaUi(page: Page, email: string, password: string) {
  await page.getByLabel(/Email/i).fill(email);
  await page.getByLabel(/^Password/i).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}
