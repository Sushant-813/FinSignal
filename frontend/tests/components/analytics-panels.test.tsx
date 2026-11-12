import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { AnalyticsPage } from "../../src/features/analytics/pages/AnalyticsPage.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildCategoriesFixture,
  buildMerchantsFixture,
  buildTrendsFixture,
} from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

vi.mock("../../src/features/analytics/components/EChartsCanvas.tsx", () => ({
  default: ({ ariaLabel }: { ariaLabel: string }) => (
    <div data-testid="mock-echarts-canvas" role="img" aria-label={ariaLabel} />
  ),
}));

function renderAnalytics(initialPath = "/analytics") {
  setAccessToken("analytics-page-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))));

  const router = createMemoryRouter([{ path: "/analytics", element: <AnalyticsPage /> }], {
    initialEntries: [initialPath],
  });

  return render(
    <QueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryProvider>
  );
}

describe("AnalyticsPage & chart panels (F3.3)", () => {
  it("loads trends, categories, and merchants cleanly and toggles accessible table views", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/analytics/trends", () => HttpResponse.json(buildTrendsFixture())),
      http.get("/api/v1/analytics/categories", () => HttpResponse.json(buildCategoriesFixture())),
      http.get("/api/v1/analytics/merchants", () => HttpResponse.json(buildMerchantsFixture()))
    );

    renderAnalytics();

    await waitFor(() => {
      expect(screen.getAllByTestId("mock-echarts-canvas")).toHaveLength(3);
    });

    // Switch all three panels to Table mode via their Table buttons
    const tableButtons = screen.getAllByRole("button", { name: "Table" });
    for (const btn of tableButtons) {
      await user.click(btn);
    }

    expect(screen.getAllByText("TRAVEL").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("48.50%")).toBeInTheDocument();
    expect(screen.getByText("Apex Airlines")).toBeInTheDocument();
    expect(screen.getByText("52,000.00")).toBeInTheDocument();
    expect(screen.getByText("42,100.75")).toBeInTheDocument();
  });

  it("prevents /analytics/trends API calls when selected daily window exceeds 366 buckets", async () => {
    let trendCalls = 0;
    server.use(
      http.get("/api/v1/analytics/trends", () => {
        trendCalls += 1;
        return HttpResponse.json(buildTrendsFixture());
      }),
      http.get("/api/v1/analytics/categories", () => HttpResponse.json(buildCategoriesFixture())),
      http.get("/api/v1/analytics/merchants", () => HttpResponse.json(buildMerchantsFixture()))
    );

    renderAnalytics("/analytics?from_date=2024-01-01&to_date=2026-01-01&interval=day");

    await waitFor(() => {
      expect(screen.getByText(/exceeding the backend limit of 366/i)).toBeInTheDocument();
    });
    expect(trendCalls).toBe(0);
  });
});
