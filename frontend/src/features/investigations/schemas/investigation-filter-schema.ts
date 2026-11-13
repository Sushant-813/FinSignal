import { z } from "zod";
import type {
  InvestigationListParams,
  InvestigationPriority,
  InvestigationStatus,
} from "../types/investigations.types.ts";

export const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const INVESTIGATION_STATUSES: readonly InvestigationStatus[] = [
  "OPEN",
  "UNDER_REVIEW",
  "RESOLVED",
] as const;

export const INVESTIGATION_PRIORITIES: readonly InvestigationPriority[] = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
] as const;

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 25;
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

const rawFilterSchema = z
  .object({
    page: z.coerce.number().int().min(1).default(DEFAULT_PAGE),
    page_size: z.coerce.number().int().min(1).max(100).default(DEFAULT_PAGE_SIZE),
    status: z.enum(["OPEN", "UNDER_REVIEW", "RESOLVED"]).optional(),
    priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
    assigned_to: z
      .string()
      .trim()
      .refine((val) => val === "" || UUID_REGEX.test(val), {
        message: "assigned_to must be a valid UUID.",
      })
      .optional(),
    unassigned: z
      .preprocess((val) => {
        if (typeof val === "string") {
          const lower = val.trim().toLowerCase();
          if (lower === "true") return true;
          if (lower === "false") return false;
        }
        return val;
      }, z.boolean().optional())
      .optional(),
  })
  .superRefine((val, ctx) => {
    // If both assigned_to and unassigned=true are explicitly provided, flag conflict
    if (val.unassigned === true && val.assigned_to && val.assigned_to.trim() !== "") {
      ctx.addIssue({
        code: "custom",
        path: ["assigned_to"],
        message: "Cannot combine assigned_to filter with unassigned=true.",
      });
    }
  });

export type RawInvestigationFilterInput = z.input<typeof rawFilterSchema>;
export type RawInvestigationFilterOutput = z.output<typeof rawFilterSchema>;

export const investigationFilterSchema = rawFilterSchema;

/**
 * Normalizes and validates URL search parameters into a safe, backend-compatible
 * InvestigationListParams object. Enforces default pagination fallbacks and resolves
 * filter conflicts fail-closed (omitting assigned_to if unassigned=true).
 */
export function parseInvestigationFilterParams(
  source: URLSearchParams | Record<string, string | string[] | undefined>
): InvestigationListParams {
  const getParam = (key: string): string | undefined => {
    if (source instanceof URLSearchParams) {
      return source.get(key) ?? undefined;
    }
    const val = source[key];
    if (Array.isArray(val)) {
      return val[0];
    }
    return val;
  };

  const rawInput: Record<string, unknown> = {};

  const pageRaw = getParam("page");
  if (pageRaw !== undefined && pageRaw.trim() !== "") {
    rawInput.page = pageRaw;
  }

  const pageSizeRaw = getParam("page_size");
  if (pageSizeRaw !== undefined && pageSizeRaw.trim() !== "") {
    rawInput.page_size = pageSizeRaw;
  }

  const statusRaw = getParam("status");
  if (statusRaw !== undefined && statusRaw.trim() !== "") {
    rawInput.status = statusRaw.trim();
  }

  const priorityRaw = getParam("priority");
  if (priorityRaw !== undefined && priorityRaw.trim() !== "") {
    rawInput.priority = priorityRaw.trim();
  }

  const assignedToRaw = getParam("assigned_to");
  if (assignedToRaw !== undefined && assignedToRaw.trim() !== "") {
    rawInput.assigned_to = assignedToRaw.trim();
  }

  const unassignedRaw = getParam("unassigned");
  if (unassignedRaw !== undefined && unassignedRaw.trim() !== "") {
    rawInput.unassigned = unassignedRaw.trim();
  }

  const parsed = rawFilterSchema.safeParse(rawInput);

  if (!parsed.success) {
    // Graceful fallback to default values on invalid input, isolating valid parameters
    const rawPage =
      typeof rawInput.page === "string" && /^[1-9]\d*$/.test(rawInput.page)
        ? Number.parseInt(rawInput.page, 10)
        : NaN;
    const fallbackPage = !Number.isNaN(rawPage) && rawPage >= 1 ? rawPage : DEFAULT_PAGE;

    const rawSize =
      typeof rawInput.page_size === "string" && /^[1-9]\d*$/.test(rawInput.page_size)
        ? Number.parseInt(rawInput.page_size, 10)
        : NaN;
    const fallbackPageSize =
      !Number.isNaN(rawSize) && rawSize >= 1 && rawSize <= 100 ? rawSize : DEFAULT_PAGE_SIZE;

    const validStatus = INVESTIGATION_STATUSES.includes(rawInput.status as InvestigationStatus)
      ? (rawInput.status as InvestigationStatus)
      : undefined;

    const validPriority = INVESTIGATION_PRIORITIES.includes(
      rawInput.priority as InvestigationPriority
    )
      ? (rawInput.priority as InvestigationPriority)
      : undefined;

    const isUnassigned =
      typeof rawInput.unassigned === "string" && rawInput.unassigned.toLowerCase() === "true";

    const validAssignedTo =
      !isUnassigned &&
      typeof rawInput.assigned_to === "string" &&
      UUID_REGEX.test(rawInput.assigned_to)
        ? rawInput.assigned_to
        : undefined;

    return {
      page: fallbackPage,
      page_size: fallbackPageSize,
      status: validStatus,
      priority: validPriority,
      assigned_to: validAssignedTo,
      unassigned: isUnassigned ? true : undefined,
    };
  }

  const data = parsed.data;
  const isUnassigned = data.unassigned === true;
  const cleanAssignedTo =
    !isUnassigned && data.assigned_to && data.assigned_to.trim() !== ""
      ? data.assigned_to.trim()
      : undefined;

  return {
    page: data.page,
    page_size: data.page_size,
    status: data.status,
    priority: data.priority,
    assigned_to: cleanAssignedTo,
    unassigned: isUnassigned ? true : undefined,
  };
}
