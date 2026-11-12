import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import {
  buildHalfOpenDateRange,
  getDefaultCivilWindow,
  isValidCivilDate,
  isValidIanaTimeZone,
} from "../../../lib/formatting/datetime.ts";
import { CURRENCY_REGEX, NAMESPACE_REGEX } from "../schemas/reporting-scope-schema.ts";
import type {
  CategoryDirection,
  MerchantSortBy,
  ReportingScope,
  TrendInterval,
} from "../types/analytics.types.ts";

export const DEFAULT_SOURCE_NAMESPACE = "SYNTHETIC";
export const DEFAULT_CURRENCY = "INR";
export const DEFAULT_TIMEZONE = "UTC";
export const DEFAULT_MERCHANT_LIMIT = 20;

export interface AnalyticsViewControls {
  readonly interval: TrendInterval;
  readonly direction: CategoryDirection;
  readonly merchantSortBy: MerchantSortBy;
  readonly merchantLimit: number;
  readonly merchantOffset: number;
}

export interface ReportingScopeResult {
  readonly scope: ReportingScope;
  readonly controls: AnalyticsViewControls;
  readonly hadInvalidUrlParams: boolean;
  readonly setScope: (next: {
    source_namespace: string;
    currency: string;
    fromDate: string;
    toDate: string;
    timezone: string;
  }) => void;
  readonly resetScope: () => void;
  readonly setInterval: (interval: TrendInterval) => void;
  readonly setDirection: (direction: CategoryDirection) => void;
  readonly setMerchantSortBy: (sortBy: MerchantSortBy) => void;
  readonly setMerchantLimit: (limit: number) => void;
  readonly setMerchantOffset: (offset: number) => void;
  readonly buildScopeSearchString: () => string;
}

export function useReportingScopeParams(): ReportingScopeResult {
  const [searchParams, setSearchParams] = useSearchParams();

  const parsed = useMemo(() => {
    const defaults = getDefaultCivilWindow();
    let hadInvalid = false;

    const rawNs = searchParams.get("source_namespace");
    let source_namespace = DEFAULT_SOURCE_NAMESPACE;
    if (rawNs !== null) {
      const trimmed = rawNs.trim();
      if (NAMESPACE_REGEX.test(trimmed)) {
        source_namespace = trimmed;
      } else {
        hadInvalid = true;
      }
    }

    const rawCurrency = searchParams.get("currency");
    let currency = DEFAULT_CURRENCY;
    if (rawCurrency !== null) {
      const upper = rawCurrency.trim().toUpperCase();
      if (CURRENCY_REGEX.test(upper)) {
        currency = upper;
      } else {
        hadInvalid = true;
      }
    }

    const rawTz = searchParams.get("timezone");
    let timezone = DEFAULT_TIMEZONE;
    if (rawTz !== null) {
      const trimmed = rawTz.trim();
      if (isValidIanaTimeZone(trimmed)) {
        timezone = trimmed;
      } else {
        hadInvalid = true;
      }
    }

    const rawFrom = searchParams.get("from_date");
    const rawTo = searchParams.get("to_date");
    let fromDate = defaults.fromDate;
    let toDate = defaults.toDate;

    if (rawFrom !== null || rawTo !== null) {
      const validFrom = rawFrom !== null && isValidCivilDate(rawFrom);
      const validTo = rawTo !== null && isValidCivilDate(rawTo);
      if (validFrom && validTo && rawFrom <= rawTo) {
        fromDate = rawFrom.trim();
        toDate = rawTo.trim();
      } else if (validFrom && rawTo === null) {
        fromDate = rawFrom.trim();
        toDate = rawFrom.trim() > defaults.toDate ? rawFrom.trim() : defaults.toDate;
        hadInvalid = true;
      } else {
        hadInvalid = true;
      }
    }

    const window = buildHalfOpenDateRange(fromDate, toDate, timezone);

    const rawInterval = searchParams.get("interval");
    const interval: TrendInterval =
      rawInterval === "day" || rawInterval === "month" ? rawInterval : "day";

    const rawDirection = searchParams.get("direction");
    const direction: CategoryDirection =
      rawDirection === "DEBIT" || rawDirection === "CREDIT" ? rawDirection : "DEBIT";

    const rawMerchantSort = searchParams.get("merchant_sort_by");
    const merchantSortBy: MerchantSortBy =
      rawMerchantSort === "amount" || rawMerchantSort === "count" ? rawMerchantSort : "amount";

    const rawLimit = searchParams.get("merchant_limit");
    const parsedLimit = rawLimit ? Number.parseInt(rawLimit, 10) : DEFAULT_MERCHANT_LIMIT;
    const merchantLimit =
      Number.isInteger(parsedLimit) && parsedLimit >= 1 && parsedLimit <= 100
        ? parsedLimit
        : DEFAULT_MERCHANT_LIMIT;

    const rawOffset = searchParams.get("merchant_offset");
    const parsedOffset = rawOffset ? Number.parseInt(rawOffset, 10) : 0;
    const merchantOffset = Number.isInteger(parsedOffset) && parsedOffset >= 0 ? parsedOffset : 0;

    return {
      scope: {
        source_namespace,
        currency,
        fromDate,
        toDate,
        timezone,
        from_time: window.fromTime,
        to_time: window.toTime,
      } satisfies ReportingScope,
      controls: {
        interval,
        direction,
        merchantSortBy,
        merchantLimit,
        merchantOffset,
      } satisfies AnalyticsViewControls,
      hadInvalidUrlParams: hadInvalid,
    };
  }, [searchParams]);

  const setScope = useCallback(
    (next: {
      source_namespace: string;
      currency: string;
      fromDate: string;
      toDate: string;
      timezone: string;
    }) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("source_namespace", next.source_namespace.trim());
        updated.set("currency", next.currency.trim().toUpperCase());
        updated.set("from_date", next.fromDate.trim());
        updated.set("to_date", next.toDate.trim());
        updated.set("timezone", next.timezone.trim());
        // Reset merchant pagination offset when scope changes
        if (updated.has("merchant_offset")) {
          updated.set("merchant_offset", "0");
        }
        return updated;
      });
    },
    [setSearchParams]
  );

  const resetScope = useCallback(() => {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      updated.delete("source_namespace");
      updated.delete("currency");
      updated.delete("from_date");
      updated.delete("to_date");
      updated.delete("timezone");
      updated.delete("merchant_offset");
      return updated;
    });
  }, [setSearchParams]);

  const setInterval = useCallback(
    (interval: TrendInterval) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("interval", interval);
        return updated;
      });
    },
    [setSearchParams]
  );

  const setDirection = useCallback(
    (direction: CategoryDirection) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("direction", direction);
        return updated;
      });
    },
    [setSearchParams]
  );

  const setMerchantSortBy = useCallback(
    (sortBy: MerchantSortBy) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("merchant_sort_by", sortBy);
        updated.set("merchant_offset", "0");
        return updated;
      });
    },
    [setSearchParams]
  );

  const setMerchantLimit = useCallback(
    (limit: number) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("merchant_limit", String(limit));
        updated.set("merchant_offset", "0");
        return updated;
      });
    },
    [setSearchParams]
  );

  const setMerchantOffset = useCallback(
    (offset: number) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("merchant_offset", String(Math.max(0, offset)));
        return updated;
      });
    },
    [setSearchParams]
  );

  const buildScopeSearchString = useCallback(() => {
    const out = new URLSearchParams();
    out.set("source_namespace", parsed.scope.source_namespace);
    out.set("currency", parsed.scope.currency);
    out.set("from_date", parsed.scope.fromDate);
    out.set("to_date", parsed.scope.toDate);
    out.set("timezone", parsed.scope.timezone);
    return `?${out.toString()}`;
  }, [parsed.scope]);

  return {
    scope: parsed.scope,
    controls: parsed.controls,
    hadInvalidUrlParams: parsed.hadInvalidUrlParams,
    setScope,
    resetScope,
    setInterval,
    setDirection,
    setMerchantSortBy,
    setMerchantLimit,
    setMerchantOffset,
    buildScopeSearchString,
  };
}
