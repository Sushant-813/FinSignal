import { z } from "zod";
import { UUID_REGEX } from "./investigation-filter-schema.ts";

export const INVESTIGATION_RESOLUTIONS = [
  "LEGITIMATE",
  "SUSPICIOUS",
  "CONFIRMED_FRAUD",
  "INCONCLUSIVE",
] as const;

/**
 * Validates request payload for manual investigation case creation.
 * Strictly forbids extra properties (such as notes or title) matching backend extra="forbid".
 */
export const investigationCreateSchema = z
  .object({
    transaction_id: z
      .string()
      .trim()
      .regex(UUID_REGEX, "Transaction ID must be a valid UUID."),
    priority: z
      .enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
      .default("MEDIUM"),
  })
  .strict();

export type InvestigationCreateFormValues = z.infer<typeof investigationCreateSchema>;

/**
 * Validates mutable attributes for an investigation case under row-level lock.
 * Supports updating assignment (UUID or explicit null to unassign),
 * urgency priority, and the sole permitted status transition (OPEN -> UNDER_REVIEW).
 */
export const investigationPatchSchema = z
  .object({
    assigned_to: z
      .union([
        z.string().trim().regex(UUID_REGEX, "Assignee must be a valid UUID."),
        z.null(),
      ])
      .optional(),
    status: z.literal("UNDER_REVIEW").optional(),
    priority: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).optional(),
  })
  .strict();

export type InvestigationPatchFormValues = z.infer<typeof investigationPatchSchema>;

/**
 * Validates request payload for explicit case resolution.
 * Requires a supported resolution outcome and mandatory, non-empty, non-whitespace notes.
 */
export const investigationResolveSchema = z
  .object({
    resolution: z.enum(INVESTIGATION_RESOLUTIONS, {
      message: "Please select a valid investigation resolution outcome.",
    }),
    resolution_notes: z
      .string()
      .trim()
      .min(1, "Resolution notes are mandatory and must contain non-whitespace text.")
      .max(4000, "Resolution notes must not exceed 4000 characters."),
  })
  .strict();

export type InvestigationResolveFormValues = z.infer<typeof investigationResolveSchema>;

/**
 * Validates payload to associate a related transaction to an active investigation.
 */
export const investigationLinkSchema = z
  .object({
    transaction_id: z
      .string()
      .trim()
      .regex(UUID_REGEX, "Transaction ID must be a valid UUID."),
  })
  .strict();

export type InvestigationLinkFormValues = z.infer<typeof investigationLinkSchema>;

