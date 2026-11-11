import { z } from "zod";

/**
 * Aligned with backend `LoginRequest` (`min_length=1, max_length=128` for password).
 * Registration password complexity (`12..128`) is intentionally not enforced at login.
 */
export const loginFormSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, "Email is required.")
    .max(255, "Email must not exceed 255 characters.")
    .email("Enter a valid email address.")
    .transform((value) => value.toLowerCase()),
  password: z
    .string()
    .min(1, "Password is required.")
    .max(128, "Password must not exceed 128 characters."),
});

export type LoginFormValues = z.infer<typeof loginFormSchema>;
