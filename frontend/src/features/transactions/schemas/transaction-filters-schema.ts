import { z } from "zod";
import { isValidCivilDate } from "../../../lib/formatting/datetime.ts";
import { compareDecimalStrings } from "../../../lib/formatting/money.ts";

export const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const NAMESPACE_REGEX = /^[A-Z0-9_]{3,64}$/;
const CURRENCY_REGEX = /^[A-Z]{3}$/;
const POSITIVE_DECIMAL_REGEX = /^\d+(?:\.\d{1,2})?$/;

const optionalUuid = z
  .string()
  .trim()
  .refine((val) => val === "" || UUID_REGEX.test(val), "Must be a valid UUID.");

const optionalPositiveAmount = z
  .string()
  .trim()
  .refine(
    (val) =>
      val === "" || (POSITIVE_DECIMAL_REGEX.test(val) && compareDecimalStrings(val, "0.01") >= 0),
    "Amount must be a decimal value >= 0.01 (up to 2 decimal places)."
  );

export const transactionFiltersFormSchema = z
  .object({
    source_namespace: z
      .string()
      .trim()
      .toUpperCase()
      .regex(NAMESPACE_REGEX, "Namespace must be 3–64 chars (A–Z, 0–9, _)."),
    direction: z.enum(["ALL", "DEBIT", "CREDIT"]),
    risk_level: z.enum(["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    currency: z
      .string()
      .trim()
      .refine(
        (val) => val === "" || CURRENCY_REGEX.test(val.toUpperCase()),
        "Currency must be a 3-letter ISO code (e.g., INR)."
      ),
    transaction_type: z.string().trim().max(32, "Transaction type must not exceed 32 characters."),
    category: z.string().trim().max(64, "Category must not exceed 64 characters."),
    fromDate: z
      .string()
      .trim()
      .refine((val) => val === "" || isValidCivilDate(val), "Enter a valid start date."),
    toDate: z
      .string()
      .trim()
      .refine((val) => val === "" || isValidCivilDate(val), "Enter a valid end date."),
    min_amount: optionalPositiveAmount,
    max_amount: optionalPositiveAmount,
    account_id: optionalUuid,
    merchant_id: optionalUuid,
    device_id: optionalUuid,
    location_id: optionalUuid,
  })
  .superRefine((val, ctx) => {
    if (val.fromDate && val.toDate && val.fromDate > val.toDate) {
      ctx.addIssue({
        code: "custom",
        path: ["toDate"],
        message: "End date must be on or after start date.",
      });
    }
    if (
      val.min_amount &&
      val.max_amount &&
      POSITIVE_DECIMAL_REGEX.test(val.min_amount) &&
      POSITIVE_DECIMAL_REGEX.test(val.max_amount) &&
      compareDecimalStrings(val.min_amount, val.max_amount) > 0
    ) {
      ctx.addIssue({
        code: "custom",
        path: ["max_amount"],
        message: "Maximum amount must be greater than or equal to minimum amount.",
      });
    }
  });

export type TransactionFiltersFormValues = z.infer<typeof transactionFiltersFormSchema>;
