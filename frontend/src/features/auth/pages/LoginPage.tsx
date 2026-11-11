import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { Alert, type AlertVariant } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import {
  extractFieldErrors,
  getUserFriendlyErrorMessage,
  isApiClientError,
} from "../../../lib/api/errors.ts";
import { sanitizeRedirectPath } from "../../../lib/auth/redirect.ts";
import { useAuth } from "../hooks/useAuth.ts";
import { loginFormSchema, type LoginFormValues } from "../schemas/login-schema.ts";

interface LoginSubmissionError {
  readonly variant: AlertVariant;
  readonly message: string;
  readonly requestId?: string | undefined;
}

function isAbortError(error: unknown): boolean {
  return (
    (error instanceof Error ||
      (typeof DOMException !== "undefined" && error instanceof DOMException)) &&
    error.name === "AbortError"
  );
}

export function LoginPage() {
  const { signIn, sessionNotice, clearSessionNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [submitError, setSubmitError] = useState<LoginSubmissionError | null>(null);

  const stateFrom =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof (location.state as { from?: unknown }).from === "string"
      ? (location.state as { from: string }).from
      : null;

  const redirectTarget = sanitizeRedirectPath(searchParams.get("redirect") ?? stateFrom);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);
    clearSessionNotice();

    try {
      await signIn({ email: values.email, password: values.password });
      void navigate(redirectTarget, { replace: true });
    } catch (error: unknown) {
      if (isAbortError(error)) {
        return;
      }

      if (isApiClientError(error)) {
        if (error.status === 401) {
          setSubmitError({
            variant: "danger",
            message: "Invalid email or password, or your account is inactive.",
            requestId: error.requestId,
          });
          return;
        }

        if (error.status === 429) {
          setSubmitError({
            variant: "warning",
            message:
              error.retryAfterSeconds !== undefined
                ? `Too many failed login attempts. Please wait ${error.retryAfterSeconds} seconds before trying again.`
                : "Too many failed login attempts. Please wait before trying again.",
            requestId: error.requestId,
          });
          return;
        }

        if (error.status === 422) {
          const fieldErrors = extractFieldErrors(error);
          let mappedField = false;
          if (fieldErrors.email?.[0]) {
            setError("email", { message: fieldErrors.email[0] });
            mappedField = true;
          }
          if (fieldErrors.password?.[0]) {
            setError("password", { message: fieldErrors.password[0] });
            mappedField = true;
          }
          if (mappedField) {
            return;
          }
        }

        setSubmitError({
          variant: "danger",
          message: getUserFriendlyErrorMessage(error),
          requestId: error.requestId,
        });
        return;
      }

      setSubmitError({
        variant: "danger",
        message: "Unable to sign in. Please check your connection and try again.",
      });
    }
  };

  return (
    <Card padding="lg" elevated>
      <CardHeader>
        <CardTitle as="h1" size="section">
          Sign in
        </CardTitle>
        <CardDescription>
          Sign in to the FinSignal investigation workspace with your assigned credentials.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {sessionNotice ? (
          <Alert variant="warning" role="status">
            {sessionNotice.message}
          </Alert>
        ) : null}

        {submitError ? (
          <Alert variant={submitError.variant} role="alert" requestId={submitError.requestId}>
            {submitError.message}
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            disabled={isSubmitting}
            error={errors.email?.message}
            {...register("email")}
          />

          <div className="relative">
            <Input
              label="Password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              disabled={isSubmitting}
              className="pr-10"
              error={errors.password?.message}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              disabled={isSubmitting}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              className="absolute right-2 top-[29px] inline-flex h-7 w-7 items-center justify-center rounded-control text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary disabled:opacity-50"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            isLoading={isSubmitting}
            disabled={isSubmitting}
          >
            Sign in
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
