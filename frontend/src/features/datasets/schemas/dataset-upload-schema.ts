import { z } from "zod";

export const MAX_UPLOAD_FILE_BYTES = 50 * 1024 * 1024; // 52,428,800 bytes (50 MB)
export const NAMESPACE_REGEX = /^[A-Z0-9_]{3,64}$/;

export function validateCsvFile(file: unknown): { valid: boolean; error?: string } {
  if (!(file instanceof File)) {
    return { valid: false, error: "Please select a file to upload." };
  }
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return { valid: false, error: "Only CSV files (.csv) are accepted for dataset import." };
  }
  if (file.size === 0) {
    return { valid: false, error: "Uploaded CSV file is empty." };
  }
  if (file.size > MAX_UPLOAD_FILE_BYTES) {
    return { valid: false, error: "File exceeds maximum allowable size of 50 MB." };
  }
  return { valid: true };
}

export const datasetUploadFormSchema = z.object({
  source_namespace: z
    .string()
    .trim()
    .regex(
      NAMESPACE_REGEX,
      "Namespace must be 3-64 characters of uppercase letters, digits, or underscores."
    )
    .default("SYNTHETIC"),
  source_type: z
    .string()
    .trim()
    .min(1, "Source type is required.")
    .max(32, "Source type must not exceed 32 characters.")
    .default("SYNTHETIC"),
});

export type DatasetUploadFormValues = z.infer<typeof datasetUploadFormSchema>;

export const datasetUploadSchema = z.object({
  file: z
    .custom<File>(
      (val) =>
        val instanceof File ||
        (typeof val === "object" && val !== null && "name" in val && "size" in val),
      {
        message: "Please select a file to upload.",
      }
    )
    .refine((file) => file.name.toLowerCase().endsWith(".csv"), {
      message: "Only CSV files (.csv) are accepted for dataset import.",
    })
    .refine((file) => file.size > 0, {
      message: "Uploaded CSV file is empty.",
    })
    .refine((file) => file.size <= MAX_UPLOAD_FILE_BYTES, {
      message: "File exceeds maximum allowable size of 50 MB.",
    }),
});
