import type { EChartsCoreOption } from "echarts/core";
import { formatShortDate } from "../../../lib/formatting/datetime.ts";
import { formatMoney, formatPercentage, toChartPlotNumber } from "../../../lib/formatting/money.ts";
import type {
  CategoryAnalyticsResponse,
  MerchantAnalyticsResponse,
  MerchantSortBy,
  TrendAnalyticsResponse,
} from "../types/analytics.types.ts";

function escapeHtml(raw: string): string {
  return raw
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function axisMoneyLabel(val: number): string {
  if (Math.abs(val) >= 1_000_000) {
    return `${(val / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(val) >= 1_000) {
    return `${(val / 1_000).toFixed(1)}k`;
  }
  return String(val);
}

export type TrendChartMetric = "amounts" | "counts";

export function buildTrendsChartOption(
  data: TrendAnalyticsResponse,
  metric: TrendChartMetric,
  reducedMotion: boolean
): EChartsCoreOption {
  const labels = data.buckets.map((b) => formatShortDate(b.bucket_start, data.timezone));
  const animation = !reducedMotion;

  if (metric === "counts") {
    return {
      animation,
      color: ["#0052FF", "#175CD3", "#4B5563"],
      tooltip: {
        trigger: "axis",
        confine: true,
        formatter: (params: unknown) => {
          const items = Array.isArray(params) ? params : [params];
          const first = items[0] as { dataIndex?: number } | undefined;
          const idx = first?.dataIndex ?? -1;
          const bucket = data.buckets[idx];
          if (!bucket) {
            return "";
          }
          const dateLabel = escapeHtml(formatShortDate(bucket.bucket_start, data.timezone));
          return [
            `<strong>${dateLabel} (${escapeHtml(data.timezone)})</strong>`,
            `Total: ${bucket.transaction_count.toLocaleString("en-US")}`,
            `Debit: ${bucket.debit_count.toLocaleString("en-US")}`,
            `Credit: ${bucket.credit_count.toLocaleString("en-US")}`,
          ].join("<br/>");
        },
      },
      legend: {
        top: 0,
        data: ["Debit count", "Credit count", "Total count"],
      },
      grid: { left: 52, right: 20, top: 40, bottom: 32, containLabel: true },
      xAxis: {
        type: "category",
        data: labels,
        axisLabel: { color: "#4B5563", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        name: "Transactions",
        nameTextStyle: { color: "#6B7280", fontSize: 11 },
        axisLabel: { color: "#4B5563", fontSize: 11 },
      },
      series: [
        {
          name: "Debit count",
          type: "bar",
          data: data.buckets.map((b) => b.debit_count),
          barMaxWidth: 24,
        },
        {
          name: "Credit count",
          type: "bar",
          data: data.buckets.map((b) => b.credit_count),
          barMaxWidth: 24,
        },
        {
          name: "Total count",
          type: "line",
          smooth: false,
          data: data.buckets.map((b) => b.transaction_count),
        },
      ],
    };
  }

  return {
    animation,
    color: ["#0052FF", "#175CD3", "#4B5563"],
    tooltip: {
      trigger: "axis",
      confine: true,
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number } | undefined;
        const idx = first?.dataIndex ?? -1;
        const bucket = data.buckets[idx];
        if (!bucket) {
          return "";
        }
        const dateLabel = escapeHtml(formatShortDate(bucket.bucket_start, data.timezone));
        const debitStr = escapeHtml(formatMoney(bucket.total_debit_amount, data.currency));
        const creditStr = escapeHtml(formatMoney(bucket.total_credit_amount, data.currency));
        const netStr = escapeHtml(formatMoney(bucket.net_cash_flow, data.currency));
        return [
          `<strong>${dateLabel} (${escapeHtml(data.timezone)})</strong>`,
          `Debit: ${debitStr}`,
          `Credit: ${creditStr}`,
          `Net cash flow: ${netStr}`,
        ].join("<br/>");
      },
    },
    legend: {
      top: 0,
      data: ["Debit amount", "Credit amount", "Net cash flow"],
    },
    grid: { left: 56, right: 20, top: 40, bottom: 32, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { color: "#4B5563", fontSize: 11 },
    },
    yAxis: {
      type: "value",
      name: data.currency,
      nameTextStyle: { color: "#6B7280", fontSize: 11 },
      axisLabel: {
        color: "#4B5563",
        fontSize: 11,
        formatter: (value: number) => axisMoneyLabel(value),
      },
    },
    series: [
      {
        name: "Debit amount",
        type: "bar",
        data: data.buckets.map((b) => toChartPlotNumber(b.total_debit_amount)),
        barMaxWidth: 24,
      },
      {
        name: "Credit amount",
        type: "bar",
        data: data.buckets.map((b) => toChartPlotNumber(b.total_credit_amount)),
        barMaxWidth: 24,
      },
      {
        name: "Net cash flow",
        type: "line",
        smooth: false,
        data: data.buckets.map((b) => toChartPlotNumber(b.net_cash_flow)),
      },
    ],
  };
}

export function buildCategoryChartOption(
  data: CategoryAnalyticsResponse,
  reducedMotion: boolean
): EChartsCoreOption {
  const ordered = [...data.categories].reverse();

  return {
    animation: !reducedMotion,
    color: ["#0052FF"],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number } | undefined;
        const idx = first?.dataIndex ?? -1;
        const cat = ordered[idx];
        if (!cat) {
          return "";
        }
        return [
          `<strong>${escapeHtml(cat.category_name)}</strong>`,
          `Total (${escapeHtml(data.direction)}): ${escapeHtml(formatMoney(cat.total_amount, data.currency))}`,
          `Share: ${escapeHtml(formatPercentage(cat.percentage_of_total))}`,
          `Transactions: ${cat.transaction_count.toLocaleString("en-US")}`,
          `Average: ${escapeHtml(formatMoney(cat.average_amount, data.currency))}`,
        ].join("<br/>");
      },
    },
    grid: { left: 24, right: 24, top: 16, bottom: 28, containLabel: true },
    xAxis: {
      type: "value",
      name: data.currency,
      nameTextStyle: { color: "#6B7280", fontSize: 11 },
      axisLabel: {
        color: "#4B5563",
        fontSize: 11,
        formatter: (value: number) => axisMoneyLabel(value),
      },
    },
    yAxis: {
      type: "category",
      data: ordered.map((c) => c.category_name),
      axisLabel: { color: "#111827", fontSize: 12 },
    },
    series: [
      {
        name: `${data.direction} amount`,
        type: "bar",
        barMaxWidth: 22,
        data: ordered.map((c) => toChartPlotNumber(c.total_amount)),
      },
    ],
  };
}

export function buildMerchantChartOption(
  data: MerchantAnalyticsResponse,
  sortBy: MerchantSortBy,
  reducedMotion: boolean
): EChartsCoreOption {
  const ordered = [...data.merchants].reverse();

  return {
    animation: !reducedMotion,
    color: ["#175CD3"],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      confine: true,
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        const first = items[0] as { dataIndex?: number } | undefined;
        const idx = first?.dataIndex ?? -1;
        const merchant = ordered[idx];
        if (!merchant) {
          return "";
        }
        return [
          `<strong>${escapeHtml(merchant.merchant_name)}</strong> (${escapeHtml(merchant.merchant_category)})`,
          `Total spend: ${escapeHtml(formatMoney(merchant.total_amount, data.currency))}`,
          `Transactions: ${merchant.transaction_count.toLocaleString("en-US")}`,
          `Average: ${escapeHtml(formatMoney(merchant.average_amount, data.currency))}`,
          `% of total debit: ${escapeHtml(formatPercentage(merchant.percentage_of_total_debit))}`,
          `% of merchant spend: ${escapeHtml(formatPercentage(merchant.percentage_of_merchant_spend))}`,
        ].join("<br/>");
      },
    },
    grid: { left: 24, right: 24, top: 16, bottom: 28, containLabel: true },
    xAxis: {
      type: "value",
      name: sortBy === "count" ? "Transactions" : data.currency,
      nameTextStyle: { color: "#6B7280", fontSize: 11 },
      axisLabel: {
        color: "#4B5563",
        fontSize: 11,
        formatter: (value: number) => (sortBy === "count" ? String(value) : axisMoneyLabel(value)),
      },
    },
    yAxis: {
      type: "category",
      data: ordered.map((m) => m.merchant_name),
      axisLabel: { color: "#111827", fontSize: 12 },
    },
    series: [
      {
        name: sortBy === "count" ? "Transactions" : "Debit spend",
        type: "bar",
        barMaxWidth: 22,
        data: ordered.map((m) =>
          sortBy === "count" ? m.transaction_count : toChartPlotNumber(m.total_amount)
        ),
      },
    ],
  };
}
