import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  getAnalyticsCategories,
  getAnalyticsMerchants,
  getAnalyticsOverview,
  getAnalyticsTrends,
} from "../../src/features/analytics/api/analytics-api.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  buildCategoriesFixture,
  buildMerchantsFixture,
  buildOverviewFixture,
  buildTrendsFixture,
} from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

describe("Analytics API wrappers (F3.1–F3.3)", () => {
  it("encodes overview, trends, categories, and merchants query parameters cleanly", async () => {
    setAccessToken("analytics-jwt");
    const capturedUrls: string[] = [];

    server.use(
      http.get("/api/v1/analytics/overview", ({ request }) => {
        capturedUrls.push(request.url);
        return HttpResponse.json(buildOverviewFixture());
      }),
      http.get("/api/v1/analytics/trends", ({ request }) => {
        capturedUrls.push(request.url);
        return HttpResponse.json(buildTrendsFixture());
      }),
      http.get("/api/v1/analytics/categories", ({ request }) => {
        capturedUrls.push(request.url);
        return HttpResponse.json(buildCategoriesFixture());
      }),
      http.get("/api/v1/analytics/merchants", ({ request }) => {
        capturedUrls.push(request.url);
        return HttpResponse.json(buildMerchantsFixture());
      })
    );

    await getAnalyticsOverview({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: null,
      to_time: undefined,
      timezone: "UTC",
    });

    await getAnalyticsTrends({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: "2026-11-01T00:00:00Z",
      to_time: "2026-11-12T00:00:00Z",
      interval: "day",
      timezone: "Asia/Kolkata",
    });

    await getAnalyticsCategories({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      direction: "CREDIT",
      from_time: "2026-11-01T00:00:00Z",
      to_time: "2026-11-12T00:00:00Z",
    });

    await getAnalyticsMerchants({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      sort_by: "count",
      limit: 10,
      offset: 20,
      timezone: "UTC",
    });

    expect(capturedUrls[0]).toContain("source_namespace=SYNTHETIC");
    expect(capturedUrls[0]).toContain("currency=INR");
    expect(capturedUrls[0]).not.toContain("from_time=");

    expect(capturedUrls[1]).toContain("interval=day");
    expect(capturedUrls[1]).toContain("timezone=Asia%2FKolkata");

    expect(capturedUrls[2]).toContain("direction=CREDIT");
    expect(capturedUrls[3]).toContain("sort_by=count");
    expect(capturedUrls[3]).toContain("limit=10");
    expect(capturedUrls[3]).toContain("offset=20");
  });
});
