import { describe, expect, it } from "vitest";
import {
  addDaysToCivilDate,
  buildHalfOpenDateRange,
  countCalendarBuckets,
  formatShortDate,
  formatTimestamp,
  getTrendBucketLimit,
  isTimezoneAwareIso,
  isValidCivilDate,
  isValidIanaTimeZone,
  MAX_DAILY_TREND_BUCKETS,
  MAX_MONTHLY_TREND_BUCKETS,
  validateHalfOpenIsoRange,
  zonedMidnightToIso,
} from "../../src/lib/formatting/datetime.ts";

describe("F3.1 timezone-aware date/range and bucket utilities", () => {
  it("validates IANA timezones, civil calendar dates, and aware ISO strings", () => {
    expect(isValidIanaTimeZone("UTC")).toBe(true);
    expect(isValidIanaTimeZone("Asia/Kolkata")).toBe(true);
    expect(isValidIanaTimeZone("Mars/Olympus")).toBe(false);

    expect(isValidCivilDate("2026-02-28")).toBe(true);
    expect(isValidCivilDate("2026-02-29")).toBe(false);
    expect(isValidCivilDate("2024-02-29")).toBe(true);
    expect(isValidCivilDate("2026-13-01")).toBe(false);

    expect(isTimezoneAwareIso("2026-11-10T00:00:00Z")).toBe(true);
    expect(isTimezoneAwareIso("2026-11-10T00:00:00+05:30")).toBe(true);
    expect(isTimezoneAwareIso("2026-11-10T00:00:00")).toBe(false);
  });

  it("constructs half-open windows across UTC, fixed offsets, and DST transitions", () => {
    expect(addDaysToCivilDate("2026-09-30", 1)).toBe("2026-10-01");
    expect(zonedMidnightToIso("2026-11-10", "UTC")).toBe("2026-11-10T00:00:00Z");
    expect(zonedMidnightToIso("2026-11-10", "Asia/Kolkata")).toBe("2026-11-10T00:00:00+05:30");

    // US DST fall-back day (Nov 1, 2026 EDT -04:00 -> Nov 2 EST -05:00)
    const dstWindow = buildHalfOpenDateRange("2026-11-01", "2026-11-01", "America/New_York");
    expect(dstWindow.fromTime).toBe("2026-11-01T00:00:00-04:00");
    expect(dstWindow.toTime).toBe("2026-11-02T00:00:00-05:00");
    expect(validateHalfOpenIsoRange(dstWindow.fromTime, dstWindow.toTime)).toBe(true);

    expect(() => buildHalfOpenDateRange("2026-11-10", "2026-11-01", "UTC")).toThrow(RangeError);
  });

  it("counts daily/monthly trend buckets matching backend 366/120 limits", () => {
    expect(getTrendBucketLimit("day")).toBe(MAX_DAILY_TREND_BUCKETS);
    expect(getTrendBucketLimit("month")).toBe(MAX_MONTHLY_TREND_BUCKETS);

    const exactYear = buildHalfOpenDateRange("2026-01-01", "2026-12-31", "UTC");
    expect(countCalendarBuckets(exactYear.fromTime, exactYear.toTime, "UTC", "day")).toBe(365);

    const leap366 = buildHalfOpenDateRange("2024-01-01", "2024-12-31", "UTC");
    expect(countCalendarBuckets(leap366.fromTime, leap366.toTime, "UTC", "day")).toBe(366);

    const over366 = buildHalfOpenDateRange("2024-01-01", "2025-01-01", "UTC");
    expect(countCalendarBuckets(over366.fromTime, over366.toTime, "UTC", "day")).toBe(367);

    expect(
      countCalendarBuckets("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", "UTC", "month")
    ).toBe(3);
  });

  it("formats timestamps and short dates gracefully for valid, null, and invalid inputs", () => {
    expect(formatTimestamp("2026-11-10T14:25:30Z", "UTC")).toBe("2026-11-10 14:25:30 UTC");
    expect(formatTimestamp("2026-11-10T14:25:30Z", "Asia/Kolkata", { includeSeconds: false })).toBe(
      "2026-11-10 19:55 Asia/Kolkata"
    );
    expect(formatTimestamp(null, "UTC")).toBe("—");
    expect(formatTimestamp("not-a-date", "UTC")).toBe("Invalid timestamp");
    expect(formatShortDate("2026-11-10T18:40:00Z", "Asia/Kolkata")).toBe("2026-11-11");
  });
});
