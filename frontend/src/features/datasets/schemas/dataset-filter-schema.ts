import { z } from "zod";
import type { DatasetImportListParams, DatasetImportStatus } from "../types/datasets.types.ts";
import { NAMESPACE_REGEX } from "./dataset-upload-schema.ts";

export const IMPORT_STATUSES: readonly DatasetImportStatus[] = [
  "PENDING",
  "PROCESSING",
  "COMPLETED",
  "FAILED",
] as const;

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

export const ISO_WITH_TZ_REGEX =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$/i;

function parseTimezoneAwareInstant(value: string | null | undefined): Date | null {
  if (!value || typeof value !== "string" || value.trim() === "") {
    return null;
  }
  const trimmed = value.trim();
  if (!ISO_WITH_TZ_REGEX.test(trimmed)) {
    return null;
  }
  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function toDateBoundaryParam(
  dateStr: string | null | undefined,
  type: "start" | "end"
): string | null {
  if (!dateStr || typeof dateStr !== "string") {
    return null;
  }
  const clean = dateStr.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(clean)) {
    return null;
  }
  const parsed = new Date(`${clean}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  // Validate calendar day match (e.g. 2026-02-31 overflows in standard Date parsing)
  const [y, m, d] = clean.split("-").map(Number);
  if (
    parsed.getUTCFullYear() !== y ||
    parsed.getUTCMonth() + 1 !== m ||
    parsed.getUTCDate() !== d
  ) {
    return null;
  }

  if (type === "start") {
    return parsed.toISOString();
  }
  // Exclusive upper boundary: next day 00:00:00.000Z
  const nextDay = new Date(parsed.getTime() + 24 * 60 * 60 * 1000);
  return nextDay.toISOString();
}

export function mapDateRangeToUtcIsoBoundaries(
  startDateStr: string | null | undefined,
  endDateStr: string | null | undefined
): { from_time?: string; to_time?: string; error?: string } {
  const cleanStart = startDateStr?.trim();
  const cleanEnd = endDateStr?.trim();

  if (!cleanStart && !cleanEnd) {
    return {};
  }

  let fromDate: Date | undefined;
  let toDate: Date | undefined;

  if (cleanStart) {
    const startIso = toDateBoundaryParam(cleanStart, "start");
    if (!startIso) {
      return { error: "Start date must be in YYYY-MM-DD format." };
    }
    fromDate = new Date(startIso);
  }

  if (cleanEnd) {
    const endIso = toDateBoundaryParam(cleanEnd, "end");
    if (!endIso) {
      return { error: "End date must be in YYYY-MM-DD format." };
    }
    toDate = new Date(endIso);
  }

  if (fromDate && toDate && fromDate.getTime() >= toDate.getTime()) {
    return { error: "Start date must be strictly earlier than end date." };
  }

  return {
    ...(fromDate ? { from_time: fromDate.toISOString() } : {}),
    ...(toDate ? { to_time: toDate.toISOString() } : {}),
  };
}

export const datasetFilterSchema = z
  .object({
    page: z.coerce.number().int().min(1).default(1),
    page_size: z.coerce.number().int().min(1).max(100).default(20),
    source_namespace: z
      .string()
      .trim()
      .regex(NAMESPACE_REGEX, "Invalid namespace format")
      .default("SYNTHETIC"),
    status: z
      .enum(["PENDING", "PROCESSING", "COMPLETED", "FAILED"])
      .nullable()
      .optional()
      .transform((val) => val ?? undefined),
    source_type: z
      .string()
      .trim()
      .min(1)
      .max(32)
      .nullable()
      .optional()
      .transform((val) => val ?? undefined),
    from_time: z
      .string()
      .trim()
      .refine(
        (val) => !val || parseTimezoneAwareInstant(val) !== null,
        "from_time must be a timezone-aware ISO 8601 timestamp"
      )
      .nullable()
      .optional()
      .transform((val) => val ?? undefined),
    to_time: z
      .string()
      .trim()
      .refine(
        (val) => !val || parseTimezoneAwareInstant(val) !== null,
        "to_time must be a timezone-aware ISO 8601 timestamp"
      )
      .nullable()
      .optional()
      .transform((val) => val ?? undefined),
  })
  .refine(
    (data) => {
      if (data.from_time && data.to_time) {
        const fromInstant = parseTimezoneAwareInstant(data.from_time);
        const toInstant = parseTimezoneAwareInstant(data.to_time);
        if (fromInstant && toInstant) {
          return fromInstant.getTime() < toInstant.getTime();
        }
      }
      return true;
    },
    {
      message: "from_time must be strictly earlier than to_time.",
      path: ["to_time"],
    }
  );

export type DatasetFilterSchemaInput = z.input<typeof datasetFilterSchema>;
export type DatasetFilterSchemaOutput = z.output<typeof datasetFilterSchema>;

export interface DatasetFilterState {
  page: number;
  page_size: number;
  source_namespace?: string | undefined;
  status?: DatasetImportStatus | undefined;
  from_date?: string | undefined;
  to_date?: string | undefined;
}

export function parseDatasetSearchParams(searchParams: URLSearchParams): DatasetFilterState {
  const pageRaw = Number.parseInt(searchParams.get("page") ?? "1", 10);
  const pageSizeRaw = Number.parseInt(searchParams.get("page_size") ?? "20", 10);
  const ns = searchParams.get("source_namespace")?.trim();
  const st = searchParams.get("status")?.trim();
  const fd = searchParams.get("from_date")?.trim();
  const td = searchParams.get("to_date")?.trim();

  const validPage = Number.isInteger(pageRaw) && pageRaw >= 1 ? pageRaw : 1;
  const validPageSize =
    Number.isInteger(pageSizeRaw) && pageSizeRaw >= 1 && pageSizeRaw <= 100 ? pageSizeRaw : 20;

  const validNs = ns && NAMESPACE_REGEX.test(ns) ? ns : undefined;
  const validStatus = (IMPORT_STATUSES as readonly string[]).includes(st ?? "")
    ? (st as DatasetImportStatus)
    : undefined;

  const isValidDate = (d?: string) => {
    if (!d || !/^\d{4}-\d{2}-\d{2}$/.test(d)) return false;
    const [y, m, day] = d.split("-").map(Number);
    const parsed = new Date(`${d}T00:00:00.000Z`);
    return (
      !Number.isNaN(parsed.getTime()) &&
      parsed.getUTCFullYear() === y &&
      parsed.getUTCMonth() + 1 === m &&
      parsed.getUTCDate() === day
    );
  };

  return {
    page: validPage,
    page_size: validPageSize,
    source_namespace: validNs,
    status: validStatus,
    from_date: isValidDate(fd) ? fd : undefined,
    to_date: isValidDate(td) ? td : undefined,
  };
}

export function parseDatasetFiltersFromParams(
  searchParams: URLSearchParams
): DatasetImportListParams {
  const raw: Record<string, string> = {};
  searchParams.forEach((val, key) => {
    if (val.trim() !== "") {
      raw[key] = val.trim();
    }
  });

  const parsed = datasetFilterSchema.safeParse(raw);
  if (!parsed.success) {
    const pageVal = Number.parseInt(raw.page || "1", 10);
    const pageSizeVal = Number.parseInt(raw.page_size || "20", 10);

    return {
      page: Number.isInteger(pageVal) && pageVal >= 1 ? pageVal : 1,
      page_size:
        Number.isInteger(pageSizeVal) && pageSizeVal >= 1 && pageSizeVal <= 100 ? pageSizeVal : 20,
      source_namespace:
        raw.source_namespace && NAMESPACE_REGEX.test(raw.source_namespace)
          ? raw.source_namespace
          : "SYNTHETIC",
      status: (IMPORT_STATUSES as readonly string[]).includes(raw.status || "")
        ? (raw.status as DatasetImportStatus)
        : undefined,
      source_type: raw.source_type || undefined,
      from_time: undefined,
      to_time: undefined,
    };
  }

  return {
    page: parsed.data.page,
    page_size: parsed.data.page_size,
    source_namespace: parsed.data.source_namespace,
    status: parsed.data.status,
    source_type: parsed.data.source_type,
    from_time: parsed.data.from_time ? new Date(parsed.data.from_time).toISOString() : undefined,
    to_time: parsed.data.to_time ? new Date(parsed.data.to_time).toISOString() : undefined,
  };
}
