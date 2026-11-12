import { zodResolver } from "@hookform/resolvers/zod";
import { RotateCcw } from "lucide-react";
import { useEffect, useMemo } from "react";
import { Controller, useForm } from "react-hook-form";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Card, CardContent } from "../../../components/ui/Card.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import { COMMON_TIMEZONES } from "../../../lib/formatting/datetime.ts";
import {
  reportingScopeSchema,
  type ReportingScopeFormValues,
} from "../schemas/reporting-scope-schema.ts";
import type { ReportingScope } from "../types/analytics.types.ts";

export interface ReportingScopeBarProps {
  scope: ReportingScope;
  hadInvalidUrlParams?: boolean | undefined;
  isFetching?: boolean | undefined;
  timezoneNote?: string | undefined;
  onApply: (next: ReportingScopeFormValues) => void;
  onReset: () => void;
}

export function ReportingScopeBar({
  scope,
  hadInvalidUrlParams = false,
  isFetching = false,
  timezoneNote,
  onApply,
  onReset,
}: ReportingScopeBarProps) {
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ReportingScopeFormValues>({
    resolver: zodResolver(reportingScopeSchema),
    defaultValues: {
      source_namespace: scope.source_namespace,
      currency: scope.currency,
      fromDate: scope.fromDate,
      toDate: scope.toDate,
      timezone: scope.timezone,
    },
  });

  useEffect(() => {
    reset({
      source_namespace: scope.source_namespace,
      currency: scope.currency,
      fromDate: scope.fromDate,
      toDate: scope.toDate,
      timezone: scope.timezone,
    });
  }, [reset, scope.currency, scope.fromDate, scope.source_namespace, scope.timezone, scope.toDate]);

  const timezoneOptions = useMemo(() => {
    const base = new Set<string>(COMMON_TIMEZONES);
    if (scope.timezone) {
      base.add(scope.timezone);
    }
    return Array.from(base).map((tz) => ({ value: tz, label: tz }));
  }, [scope.timezone]);

  return (
    <Card padding="sm" as="section" aria-label="Reporting scope filters">
      <CardContent className="space-y-3">
        {hadInvalidUrlParams ? (
          <Alert variant="warning" role="status">
            One or more URL filter parameters were invalid and were normalized to safe defaults.
          </Alert>
        ) : null}

        <form
          onSubmit={handleSubmit(onApply)}
          noValidate
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6"
        >
          <Input
            label="Namespace"
            placeholder="SYNTHETIC"
            autoComplete="off"
            error={errors.source_namespace?.message}
            {...register("source_namespace")}
          />

          <Input
            label="Currency (ISO)"
            placeholder="INR"
            maxLength={3}
            autoComplete="off"
            list="fs-currency-suggestions"
            error={errors.currency?.message}
            {...register("currency")}
          />

          <Input
            label="From date (inclusive)"
            type="date"
            error={errors.fromDate?.message}
            {...register("fromDate")}
          />

          <Input
            label="To date (inclusive)"
            type="date"
            error={errors.toDate?.message}
            {...register("toDate")}
          />

          <Controller
            control={control}
            name="timezone"
            render={({ field }) => (
              <Select
                label="Reporting timezone"
                value={field.value}
                onValueChange={field.onChange}
                options={timezoneOptions}
                error={errors.timezone?.message}
              />
            )}
          />

          <div className="flex items-end gap-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isFetching}
              className="flex-1"
            >
              Apply scope
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="icon"
              onClick={onReset}
              aria-label="Reset reporting scope"
              title="Reset reporting scope"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </form>

        <datalist id="fs-currency-suggestions">
          <option value="INR" />
          <option value="USD" />
          <option value="EUR" />
          <option value="GBP" />
        </datalist>

        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-2.5 text-xs text-text-muted">
          <span>Active window:</span>
          <Badge variant="neutral">Namespace: {scope.source_namespace}</Badge>
          <Badge variant="neutral">Currency: {scope.currency}</Badge>
          <Badge variant="neutral">TZ: {scope.timezone}</Badge>
          <span className="font-mono break-all tabular-nums text-text-secondary">
            [{scope.from_time}, {scope.to_time})
          </span>
          {timezoneNote ? <span className="text-text-muted">{timezoneNote}</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}
