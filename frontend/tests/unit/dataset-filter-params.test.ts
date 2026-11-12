import { describe, expect, it } from "vitest";
import {
  datasetFilterSchema,
  parseDatasetSearchParams,
  toDateBoundaryParam,
} from "../../src/features/datasets/schemas/dataset-filter-schema.ts";

describe("datasetFilterSchema and helpers (F4.2)", () => {
  it("converts valid YYYY-MM-DD to inclusive start and exclusive end in UTC", () => {
    expect(toDateBoundaryParam("2026-11-01", "start")).toBe(
      "2026-11-01T00:00:00.000Z"
    );
    expect(toDateBoundaryParam("2026-11-01", "end")).toBe(
      "2026-11-02T00:00:00.000Z"
    );
    // Month rollover test
    expect(toDateBoundaryParam("2026-11-30", "end")).toBe(
      "2026-12-01T00:00:00.000Z"
    );
    // Leap year test
    expect(toDateBoundaryParam("2024-02-28", "end")).toBe(
      "2024-02-29T00:00:00.000Z"
    );
    expect(toDateBoundaryParam("2024-02-29", "end")).toBe(
      "2024-03-01T00:00:00.000Z"
    );
  });

  it("returns null for malformed or non-date strings", () => {
    expect(toDateBoundaryParam("", "start")).toBeNull();
    expect(toDateBoundaryParam(null, "start")).toBeNull();
    expect(toDateBoundaryParam(undefined, "start")).toBeNull();
    expect(toDateBoundaryParam("invalid-date", "start")).toBeNull();
    expect(toDateBoundaryParam("2026-02-31", "start")).toBeNull();
  });

  it("parses URL search params into sanitized DatasetFilterState", () => {
    const params = new URLSearchParams({
      page: "3",
      page_size: "50",
      source_namespace: "SYNTHETIC",
      status: "COMPLETED",
      from_date: "2026-11-01",
      to_date: "2026-11-10",
    });

    const parsed = parseDatasetSearchParams(params);
    expect(parsed).toEqual({
      page: 3,
      page_size: 50,
      source_namespace: "SYNTHETIC",
      status: "COMPLETED",
      from_date: "2026-11-01",
      to_date: "2026-11-10",
    });
  });

  it("falls back gracefully on invalid or corrupted search params", () => {
    const params = new URLSearchParams({
      page: "-5",
      page_size: "9999",
      source_namespace: "",
      status: "NOT_A_REAL_STATUS",
      from_date: "garbage",
      to_date: "2026-13-45",
    });

    const parsed = parseDatasetSearchParams(params);
    expect(parsed.page).toBe(1);
    expect(parsed.page_size).toBe(20);
    expect(parsed.source_namespace).toBeUndefined();
    expect(parsed.status).toBeUndefined();
    expect(parsed.from_date).toBeUndefined();
    expect(parsed.to_date).toBeUndefined();
  });

  it("validates namespace uppercase alphanumeric schema", () => {
    expect(
      datasetFilterSchema.safeParse({ source_namespace: "SYNTHETIC_DATA_01" }).success
    ).toBe(true);
    expect(
      datasetFilterSchema.safeParse({ source_namespace: "synthetic-lowercase" }).success
    ).toBe(false);
  });
});

