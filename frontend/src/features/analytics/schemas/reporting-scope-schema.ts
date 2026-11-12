import { z } from "zod";
import { isValidCivilDate, isValidIanaTimeZone } from "../../../lib/formatting/datetime.ts";

export const NAMESPACE_REGEX = /^[A-Z0-9_]{3,64}$/;
export const CURRENCY_REGEX = /^[A-Z]{3}$/;

export const reportingScopeSchema = z
  .object({
    source_namespace: z
      .string()
      .trim()
      .toUpperCase()
      .regex(
        NAMESPACE_REGEX,
        "Namespace must be 3–64 characters using uppercase letters, digits, or underscores."
      ),
    currency: z
      .string()
      .trim()
      .toUpperCase()
      .regex(CURRENCY_REGEX, "Currency must be a 3-letter ISO-4217 code (e.g., INR, USD)."),
    fromDate: z.string().trim().refine(isValidCivilDate, "Enter a valid start date (YYYY-MM-DD)."),
    toDate: z.string().trim().refine(isValidCivilDate, "Enter a valid end date (YYYY-MM-DD)."),
    timezone: z
      .string()
      .trim()
      .min(1, "Timezone is required.")
      .max(64, "Timezone must not exceed 64 characters.")
      .refine(isValidIanaTimeZone, "Enter a valid IANA timezone (e.g., UTC, Asia/Kolkata)."),
  })
  .refine((val) => val.fromDate <= val.toDate, {
    path: ["toDate"],
    message: "End date must be on or after start date.",
  });

export type ReportingScopeFormValues = z.infer<typeof reportingScopeSchema>;
