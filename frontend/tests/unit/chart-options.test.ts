import { describe, expect, it } from "vitest";
import {
  buildCategoryChartOption,
  buildMerchantChartOption,
  buildTrendsChartOption,
} from "../../src/features/analytics/utils/chart-options.ts";
import {
  buildCategoriesFixture,
  buildMerchantsFixture,
  buildTrendsFixture,
} from "../fixtures/f3-data.ts";

describe("Analytics ECharts option builders (F3.3)", () => {
  it("builds Trends chart options for amounts and counts with reduced-motion and XSS-escaped tooltips", () => {
    const trends = buildTrendsFixture();

    const amountsOpt = buildTrendsChartOption(trends, "amounts", true) as {
      animation?: boolean;
      tooltip?: { formatter?: (params: unknown) => string };
      series?: Array<{ name?: string; data?: unknown[] }>;
    };
    expect(amountsOpt.animation).toBe(false);
    expect(amountsOpt.series?.map((s) => s.name)).toEqual([
      "Debit amount",
      "Credit amount",
      "Net cash flow",
    ]);

    const tooltipHtml = amountsOpt.tooltip?.formatter?.([{ dataIndex: 0 }]) ?? "";
    expect(tooltipHtml).toContain("18,400.50 INR");
    expect(tooltipHtml).toContain("-9,200.50 INR");

    const countsOpt = buildTrendsChartOption(trends, "counts", false) as {
      animation?: boolean;
      tooltip?: { formatter?: (params: unknown) => string };
      series?: Array<{ name?: string }>;
    };
    expect(countsOpt.animation).toBe(true);
    expect(countsOpt.series?.map((s) => s.name)).toEqual([
      "Debit count",
      "Credit count",
      "Total count",
    ]);
    expect(countsOpt.tooltip?.formatter?.([{ dataIndex: 0 }])).toContain("Total: 12");
  });

  it("escapes untrusted HTML characters in Category and Merchant chart tooltips", () => {
    const xssCategories = buildCategoriesFixture({
      categories: [
        {
          category_name: "<script>alert(1)</script>",
          transaction_count: 5,
          total_amount: "5000.00",
          percentage_of_total: "100.00",
          average_amount: "1000.00",
        },
      ],
    });
    const catOpt = buildCategoryChartOption(xssCategories, true) as {
      tooltip?: { formatter?: (params: unknown) => string };
    };
    const catHtml = catOpt.tooltip?.formatter?.([{ dataIndex: 0 }]) ?? "";
    expect(catHtml).not.toContain("<script>");
    expect(catHtml).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(catHtml).toContain("5,000.00 INR");

    const xssMerchants = buildMerchantsFixture({
      merchants: [
        {
          merchant_id: "11111111-1111-4111-8111-111111111111",
          merchant_name: '<img src=x onerror="alert(2)">',
          merchant_category: "RETAIL",
          transaction_count: 3,
          total_amount: "7500.00",
          average_amount: "2500.00",
          percentage_of_total_debit: "7.50",
          percentage_of_merchant_spend: "10.00",
        },
      ],
    });
    const merchOpt = buildMerchantChartOption(xssMerchants, "amount", true) as {
      tooltip?: { formatter?: (params: unknown) => string };
    };
    const merchHtml = merchOpt.tooltip?.formatter?.([{ dataIndex: 0 }]) ?? "";
    expect(merchHtml).not.toContain("<img");
    expect(merchHtml).toContain("&lt;img src=x onerror=&quot;alert(2)&quot;&gt;");
    expect(merchHtml).toContain("7,500.00 INR");
  });
});
