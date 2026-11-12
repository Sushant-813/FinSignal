import { describe, expect, it } from "vitest";
import { analyticsKeys, riskKeys, transactionKeys } from "../../src/lib/api/query-keys.ts";

describe("F3 query key factory isolation and normalization", () => {
  it("normalizes optional analytics params and separates namespaces, currencies, and timezones", () => {
    const keyA = analyticsKeys.overview({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: "  ",
      to_time: undefined,
    });
    const keyB = analyticsKeys.overview({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: null,
      to_time: null,
      timezone: "UTC",
    });
    expect(keyA).toEqual(keyB);

    const keyUsd = analyticsKeys.overview({
      source_namespace: "SYNTHETIC",
      currency: "USD",
      from_time: null,
      to_time: null,
    });
    expect(keyA).not.toEqual(keyUsd);

    const trendUtc = analyticsKeys.trends({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: "2026-10-01T00:00:00Z",
      to_time: "2026-11-01T00:00:00Z",
      interval: "day",
      timezone: "UTC",
    });
    const trendIst = analyticsKeys.trends({
      source_namespace: "SYNTHETIC",
      currency: "INR",
      from_time: "2026-10-01T00:00:00Z",
      to_time: "2026-11-01T00:00:00Z",
      interval: "day",
      timezone: "Asia/Kolkata",
    });
    expect(trendUtc).not.toEqual(trendIst);
  });

  it("isolates transaction list filters and risk transaction keys without token material", () => {
    const baseFilters = {
      page: 1,
      page_size: 50,
      source_namespace: "SYNTHETIC",
      sort_by: "occurred_at" as const,
      sort_order: "desc" as const,
      account_id: "   ",
      category: undefined,
    };
    const explicitNullFilters = {
      ...baseFilters,
      account_id: null,
      category: null,
    };

    expect(transactionKeys.list(baseFilters)).toEqual(transactionKeys.list(explicitNullFilters));
    expect(transactionKeys.detail("tx-1", "SYNTHETIC")).not.toEqual(
      transactionKeys.detail("tx-1", "PROD")
    );
    expect(riskKeys.byTransaction("tx-1")).toEqual(["risk", "transaction", "tx-1"]);
    expect(JSON.stringify(riskKeys.byTransaction("tx-1"))).not.toContain("Bearer");
  });
});
