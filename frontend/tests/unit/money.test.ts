import { describe, expect, it } from "vitest";
import {
  compareDecimalStrings,
  formatDecimalString,
  formatMoney,
  formatMoneyParts,
  formatPercentage,
  isValidCurrencyCode,
  isValidDecimalString,
  toChartPlotNumber,
} from "../../src/lib/formatting/money.ts";

describe("F3.1 money formatting and string-safe decimal utilities", () => {
  it("preserves exact precision, trailing zeros, and grouping without float coercion", () => {
    expect(formatDecimalString("1234.50")).toBe("1,234.50");
    expect(formatDecimalString("9007199254740993.1234")).toBe("9,007,199,254,740,993.1234");
    expect(formatDecimalString("-1500.25")).toBe("-1,500.25");
    expect(formatDecimalString("-0.00")).toBe("0.00");
    expect(formatDecimalString("00042.5")).toBe("42.5");
    expect(() => formatDecimalString("12.34.56")).toThrow(RangeError);
    expect(() => formatDecimalString("abc")).toThrow(RangeError);
  });

  it("formats money parts and combined strings safely", () => {
    expect(formatMoneyParts("10000.00", "inr")).toEqual({
      amount: "10,000.00",
      currency: "INR",
      isNegative: false,
    });
    expect(formatMoney("-250.75", "USD")).toBe("-250.75 USD");
    expect(formatMoney(null, "INR")).toBe("—");
    expect(formatMoneyParts("   ", "INR")).toBeNull();
    expect(() => formatMoney("100.00", "US")).toThrow(RangeError);
  });

  it("validates decimals, currency codes, percentages, and exact comparisons", () => {
    expect(isValidDecimalString("123.45")).toBe(true);
    expect(isValidDecimalString("Infinity")).toBe(false);
    expect(isValidCurrencyCode("INR")).toBe(true);
    expect(isValidCurrencyCode("inr")).toBe(false);

    expect(formatPercentage("48.50")).toBe("48.50%");
    expect(formatPercentage(undefined)).toBe("—");

    expect(compareDecimalStrings("9007199254740993.00", "9007199254740992.99")).toBe(1);
    expect(compareDecimalStrings("10.5", "10.50")).toBe(0);
    expect(compareDecimalStrings("-20.00", "-10.00")).toBe(-1);

    expect(toChartPlotNumber("1234.50")).toBe(1234.5);
    expect(() => toChartPlotNumber("NaN")).toThrow(RangeError);
  });
});
