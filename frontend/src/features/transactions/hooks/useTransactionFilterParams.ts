import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import {
  addDaysToCivilDate,
  isoToCivilDateInTimeZone,
  isTimezoneAwareIso,
  isValidCivilDate,
  zonedMidnightToIso,
} from "../../../lib/formatting/datetime.ts";
import { compareDecimalStrings, isValidDecimalString } from "../../../lib/formatting/money.ts";
import { UUID_REGEX } from "../schemas/transaction-filters-schema.ts";
import type {
  TransactionDirection,
  TransactionListFilters,
  TransactionRiskLevel,
  TransactionSortField,
  TransactionSortOrder,
} from "../types/transactions.types.ts";

export const DEFAULT_TX_NAMESPACE = "SYNTHETIC";
export const DEFAULT_TX_PAGE = 1;
export const DEFAULT_TX_PAGE_SIZE = 50;
export const DEFAULT_TX_SORT_BY: TransactionSortField = "occurred_at";
export const DEFAULT_TX_SORT_ORDER: TransactionSortOrder = "desc";

const NAMESPACE_REGEX = /^[A-Z0-9_]{3,64}$/;
const CURRENCY_REGEX = /^[A-Z]{3}$/;

export interface TransactionFilterParamsResult {
  readonly filters: TransactionListFilters;
  readonly formDates: { fromDate: string; toDate: string };
  readonly activeFilterCount: number;
  readonly hadInvalidUrlParams: boolean;
  readonly applyFilters: (next: {
    source_namespace: string;
    account_id: string;
    merchant_id: string;
    device_id: string;
    location_id: string;
    transaction_type: string;
    direction: "ALL" | TransactionDirection;
    category: string;
    currency: string;
    fromDate: string;
    toDate: string;
    min_amount: string;
    max_amount: string;
    risk_level: "ALL" | TransactionRiskLevel;
  }) => void;
  readonly resetFilters: () => void;
  readonly setPage: (page: number) => void;
  readonly setPageSize: (pageSize: number) => void;
  readonly toggleSort: (field: TransactionSortField) => void;
}

export function useTransactionFilterParams(): TransactionFilterParamsResult {
  const [searchParams, setSearchParams] = useSearchParams();

  const parsed = useMemo(() => {
    let hadInvalid = false;

    const rawPage = searchParams.get("page");
    let page = DEFAULT_TX_PAGE;
    if (rawPage !== null) {
      const n = Number.parseInt(rawPage, 10);
      if (Number.isInteger(n) && n >= 1) {
        page = n;
      } else {
        hadInvalid = true;
      }
    }

    const rawPageSize = searchParams.get("page_size");
    let page_size = DEFAULT_TX_PAGE_SIZE;
    if (rawPageSize !== null) {
      const n = Number.parseInt(rawPageSize, 10);
      if (Number.isInteger(n) && n >= 1 && n <= 100) {
        page_size = n;
      } else {
        hadInvalid = true;
      }
    }

    const rawNs = searchParams.get("source_namespace");
    let source_namespace = DEFAULT_TX_NAMESPACE;
    if (rawNs !== null) {
      const trimmed = rawNs.trim();
      if (NAMESPACE_REGEX.test(trimmed)) {
        source_namespace = trimmed;
      } else {
        hadInvalid = true;
      }
    }

    const parseOptionalUuid = (key: string): string | null => {
      const raw = searchParams.get(key);
      if (raw === null || raw.trim() === "") {
        return null;
      }
      if (UUID_REGEX.test(raw.trim())) {
        return raw.trim();
      }
      hadInvalid = true;
      return null;
    };

    const account_id = parseOptionalUuid("account_id");
    const merchant_id = parseOptionalUuid("merchant_id");
    const device_id = parseOptionalUuid("device_id");
    const location_id = parseOptionalUuid("location_id");

    const rawType = searchParams.get("transaction_type");
    let transaction_type: string | null = null;
    if (rawType !== null && rawType.trim() !== "") {
      if (rawType.trim().length <= 32) {
        transaction_type = rawType.trim();
      } else {
        hadInvalid = true;
      }
    }

    const rawDir = searchParams.get("direction");
    let direction: TransactionDirection | null = null;
    if (rawDir !== null && rawDir.trim() !== "") {
      if (rawDir === "DEBIT" || rawDir === "CREDIT") {
        direction = rawDir;
      } else {
        hadInvalid = true;
      }
    }

    const rawCat = searchParams.get("category");
    let category: string | null = null;
    if (rawCat !== null && rawCat.trim() !== "") {
      if (rawCat.trim().length <= 64) {
        category = rawCat.trim();
      } else {
        hadInvalid = true;
      }
    }

    const rawCur = searchParams.get("currency");
    let currency: string | null = null;
    if (rawCur !== null && rawCur.trim() !== "") {
      const upper = rawCur.trim().toUpperCase();
      if (CURRENCY_REGEX.test(upper)) {
        currency = upper;
      } else {
        hadInvalid = true;
      }
    }

    const rawRisk = searchParams.get("risk_level");
    let risk_level: TransactionRiskLevel | null = null;
    if (rawRisk !== null && rawRisk.trim() !== "") {
      if (
        rawRisk === "LOW" ||
        rawRisk === "MEDIUM" ||
        rawRisk === "HIGH" ||
        rawRisk === "CRITICAL"
      ) {
        risk_level = rawRisk;
      } else {
        hadInvalid = true;
      }
    }

    const rawFromTime = searchParams.get("from_time");
    const rawToTime = searchParams.get("to_time");
    let from_time: string | null = null;
    let to_time: string | null = null;
    if (rawFromTime !== null && rawFromTime.trim() !== "") {
      if (isTimezoneAwareIso(rawFromTime)) {
        from_time = rawFromTime.trim();
      } else {
        hadInvalid = true;
      }
    }
    if (rawToTime !== null && rawToTime.trim() !== "") {
      if (isTimezoneAwareIso(rawToTime)) {
        to_time = rawToTime.trim();
      } else {
        hadInvalid = true;
      }
    }
    if (from_time && to_time && Date.parse(from_time) >= Date.parse(to_time)) {
      hadInvalid = true;
      from_time = null;
      to_time = null;
    }

    const rawMinAmt = searchParams.get("min_amount");
    const rawMaxAmt = searchParams.get("max_amount");
    let min_amount: string | null = null;
    let max_amount: string | null = null;
    if (rawMinAmt !== null && rawMinAmt.trim() !== "") {
      if (isValidDecimalString(rawMinAmt) && compareDecimalStrings(rawMinAmt, "0.01") >= 0) {
        min_amount = rawMinAmt.trim();
      } else {
        hadInvalid = true;
      }
    }
    if (rawMaxAmt !== null && rawMaxAmt.trim() !== "") {
      if (isValidDecimalString(rawMaxAmt) && compareDecimalStrings(rawMaxAmt, "0.01") >= 0) {
        max_amount = rawMaxAmt.trim();
      } else {
        hadInvalid = true;
      }
    }
    if (min_amount && max_amount && compareDecimalStrings(min_amount, max_amount) > 0) {
      hadInvalid = true;
      min_amount = null;
      max_amount = null;
    }

    const rawSortBy = searchParams.get("sort_by");
    let sort_by: TransactionSortField = DEFAULT_TX_SORT_BY;
    if (rawSortBy !== null) {
      if (rawSortBy === "occurred_at" || rawSortBy === "amount" || rawSortBy === "created_at") {
        sort_by = rawSortBy;
      } else {
        hadInvalid = true;
      }
    }

    const rawSortOrder = searchParams.get("sort_order");
    let sort_order: TransactionSortOrder = DEFAULT_TX_SORT_ORDER;
    if (rawSortOrder !== null) {
      const lowered = rawSortOrder.toLowerCase();
      if (lowered === "asc" || lowered === "desc") {
        sort_order = lowered;
      } else {
        hadInvalid = true;
      }
    }

    const fromDate = from_time ? isoToCivilDateInTimeZone(from_time, "UTC") : "";
    let toDate = "";
    if (to_time) {
      const exclusiveCivil = isoToCivilDateInTimeZone(to_time, "UTC");
      toDate = addDaysToCivilDate(exclusiveCivil, -1);
      if (fromDate && toDate < fromDate) {
        toDate = fromDate;
      }
    }

    const filters: TransactionListFilters = {
      page,
      page_size,
      source_namespace,
      account_id,
      merchant_id,
      device_id,
      location_id,
      transaction_type,
      direction,
      category,
      currency,
      from_time,
      to_time,
      min_amount,
      max_amount,
      risk_level,
      sort_by,
      sort_order,
    };

    const activeFilterCount = [
      account_id,
      merchant_id,
      device_id,
      location_id,
      transaction_type,
      direction,
      category,
      currency,
      from_time,
      to_time,
      min_amount,
      max_amount,
      risk_level,
    ].filter((v) => v !== null).length;

    return {
      filters,
      formDates: { fromDate, toDate },
      activeFilterCount,
      hadInvalidUrlParams: hadInvalid,
    };
  }, [searchParams]);

  const applyFilters = useCallback(
    (next: {
      source_namespace: string;
      account_id: string;
      merchant_id: string;
      device_id: string;
      location_id: string;
      transaction_type: string;
      direction: "ALL" | TransactionDirection;
      category: string;
      currency: string;
      fromDate: string;
      toDate: string;
      min_amount: string;
      max_amount: string;
      risk_level: "ALL" | TransactionRiskLevel;
    }) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams();
        updated.set("page", "1");
        updated.set("page_size", prev.get("page_size") ?? String(DEFAULT_TX_PAGE_SIZE));
        updated.set("source_namespace", next.source_namespace.trim());
        updated.set("sort_by", prev.get("sort_by") ?? DEFAULT_TX_SORT_BY);
        updated.set("sort_order", prev.get("sort_order") ?? DEFAULT_TX_SORT_ORDER);

        const setIfNonEmpty = (key: string, val: string) => {
          const trimmed = val.trim();
          if (trimmed !== "") {
            updated.set(key, trimmed);
          }
        };

        setIfNonEmpty("account_id", next.account_id);
        setIfNonEmpty("merchant_id", next.merchant_id);
        setIfNonEmpty("device_id", next.device_id);
        setIfNonEmpty("location_id", next.location_id);
        setIfNonEmpty("transaction_type", next.transaction_type);
        if (next.direction !== "ALL") {
          updated.set("direction", next.direction);
        }
        setIfNonEmpty("category", next.category);
        if (next.currency.trim() !== "") {
          updated.set("currency", next.currency.trim().toUpperCase());
        }
        if (next.risk_level !== "ALL") {
          updated.set("risk_level", next.risk_level);
        }
        if (isValidCivilDate(next.fromDate)) {
          updated.set("from_time", zonedMidnightToIso(next.fromDate, "UTC"));
        }
        if (isValidCivilDate(next.toDate)) {
          updated.set("to_time", zonedMidnightToIso(addDaysToCivilDate(next.toDate, 1), "UTC"));
        }
        setIfNonEmpty("min_amount", next.min_amount);
        setIfNonEmpty("max_amount", next.max_amount);

        return updated;
      });
    },
    [setSearchParams]
  );

  const resetFilters = useCallback(() => {
    setSearchParams(new URLSearchParams());
  }, [setSearchParams]);

  const setPage = useCallback(
    (page: number) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("page", String(Math.max(1, page)));
        return updated;
      });
    },
    [setSearchParams]
  );

  const setPageSize = useCallback(
    (pageSize: number) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        updated.set("page_size", String(pageSize));
        updated.set("page", "1");
        return updated;
      });
    },
    [setSearchParams]
  );

  const toggleSort = useCallback(
    (field: TransactionSortField) => {
      setSearchParams((prev) => {
        const updated = new URLSearchParams(prev);
        const currentBy = prev.get("sort_by") ?? DEFAULT_TX_SORT_BY;
        const currentOrder = (prev.get("sort_order") ?? DEFAULT_TX_SORT_ORDER).toLowerCase();

        const nextOrder: TransactionSortOrder =
          currentBy === field ? (currentOrder === "desc" ? "asc" : "desc") : "desc";

        updated.set("sort_by", field);
        updated.set("sort_order", nextOrder);
        updated.set("page", "1");
        return updated;
      });
    },
    [setSearchParams]
  );

  return {
    filters: parsed.filters,
    formDates: parsed.formDates,
    activeFilterCount: parsed.activeFilterCount,
    hadInvalidUrlParams: parsed.hadInvalidUrlParams,
    applyFilters,
    resetFilters,
    setPage,
    setPageSize,
    toggleSort,
  };
}
