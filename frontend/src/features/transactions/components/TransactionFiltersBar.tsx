import { zodResolver } from "@hookform/resolvers/zod";
import { Filter, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Card, CardContent } from "../../../components/ui/Card.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import {
  transactionFiltersFormSchema,
  type TransactionFiltersFormValues,
} from "../schemas/transaction-filters-schema.ts";
import type { TransactionListFilters } from "../types/transactions.types.ts";

export interface TransactionFiltersBarProps {
  filters: TransactionListFilters;
  formDates: { fromDate: string; toDate: string };
  activeFilterCount: number;
  hadInvalidUrlParams?: boolean | undefined;
  isFetching?: boolean | undefined;
  onApply: (values: TransactionFiltersFormValues) => void;
  onReset: () => void;
}

export function TransactionFiltersBar({
  filters,
  formDates,
  activeFilterCount,
  hadInvalidUrlParams = false,
  isFetching = false,
  onApply,
  onReset,
}: TransactionFiltersBarProps) {
  const hasAdvancedValues = Boolean(
    filters.account_id ||
    filters.merchant_id ||
    filters.device_id ||
    filters.location_id ||
    filters.transaction_type ||
    filters.category ||
    filters.min_amount ||
    filters.max_amount
  );
  const [showAdvanced, setShowAdvanced] = useState(hasAdvancedValues);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TransactionFiltersFormValues>({
    resolver: zodResolver(transactionFiltersFormSchema),
    defaultValues: {
      source_namespace: filters.source_namespace,
      direction: filters.direction ?? "ALL",
      risk_level: filters.risk_level ?? "ALL",
      currency: filters.currency ?? "",
      transaction_type: filters.transaction_type ?? "",
      category: filters.category ?? "",
      fromDate: formDates.fromDate,
      toDate: formDates.toDate,
      min_amount: filters.min_amount ?? "",
      max_amount: filters.max_amount ?? "",
      account_id: filters.account_id ?? "",
      merchant_id: filters.merchant_id ?? "",
      device_id: filters.device_id ?? "",
      location_id: filters.location_id ?? "",
    },
  });

  useEffect(() => {
    reset({
      source_namespace: filters.source_namespace,
      direction: filters.direction ?? "ALL",
      risk_level: filters.risk_level ?? "ALL",
      currency: filters.currency ?? "",
      transaction_type: filters.transaction_type ?? "",
      category: filters.category ?? "",
      fromDate: formDates.fromDate,
      toDate: formDates.toDate,
      min_amount: filters.min_amount ?? "",
      max_amount: filters.max_amount ?? "",
      account_id: filters.account_id ?? "",
      merchant_id: filters.merchant_id ?? "",
      device_id: filters.device_id ?? "",
      location_id: filters.location_id ?? "",
    });
  }, [filters, formDates.fromDate, formDates.toDate, reset]);

  return (
    <Card padding="sm" as="section" aria-label="Transaction filters">
      <CardContent className="space-y-3">
        {hadInvalidUrlParams ? (
          <Alert variant="warning" role="status">
            One or more invalid URL query parameters were ignored or reset to defaults.
          </Alert>
        ) : null}

        <form onSubmit={handleSubmit(onApply)} noValidate className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Input
              label="Namespace"
              placeholder="SYNTHETIC"
              autoComplete="off"
              error={errors.source_namespace?.message}
              {...register("source_namespace")}
            />

            <Controller
              control={control}
              name="direction"
              render={({ field }) => (
                <Select
                  label="Direction"
                  value={field.value}
                  onValueChange={field.onChange}
                  options={[
                    { value: "ALL", label: "All directions" },
                    { value: "DEBIT", label: "DEBIT" },
                    { value: "CREDIT", label: "CREDIT" },
                  ]}
                />
              )}
            />

            <Controller
              control={control}
              name="risk_level"
              render={({ field }) => (
                <Select
                  label="Latest risk level"
                  value={field.value}
                  onValueChange={field.onChange}
                  options={[
                    { value: "ALL", label: "All risk levels" },
                    { value: "CRITICAL", label: "CRITICAL" },
                    { value: "HIGH", label: "HIGH" },
                    { value: "MEDIUM", label: "MEDIUM" },
                    { value: "LOW", label: "LOW" },
                  ]}
                />
              )}
            />

            <Input
              label="Currency"
              placeholder="Any (e.g. INR)"
              maxLength={3}
              autoComplete="off"
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
          </div>

          {showAdvanced ? (
            <div className="grid grid-cols-1 gap-3 border-t border-border pt-3 sm:grid-cols-2 lg:grid-cols-4">
              <Input
                label="Transaction type"
                placeholder="e.g. PURCHASE, TRANSFER"
                autoComplete="off"
                error={errors.transaction_type?.message}
                {...register("transaction_type")}
              />
              <Input
                label="Category"
                placeholder="e.g. GROCERY"
                autoComplete="off"
                error={errors.category?.message}
                {...register("category")}
              />
              <Input
                label="Minimum amount"
                placeholder=">= 0.01"
                inputMode="decimal"
                autoComplete="off"
                error={errors.min_amount?.message}
                {...register("min_amount")}
              />
              <Input
                label="Maximum amount"
                placeholder=">= 0.01"
                inputMode="decimal"
                autoComplete="off"
                error={errors.max_amount?.message}
                {...register("max_amount")}
              />
              <Input
                label="Account UUID"
                placeholder="00000000-0000-0000-0000-000000000000"
                autoComplete="off"
                error={errors.account_id?.message}
                {...register("account_id")}
              />
              <Input
                label="Merchant UUID"
                placeholder="00000000-0000-0000-0000-000000000000"
                autoComplete="off"
                error={errors.merchant_id?.message}
                {...register("merchant_id")}
              />
              <Input
                label="Device UUID"
                placeholder="00000000-0000-0000-0000-000000000000"
                autoComplete="off"
                error={errors.device_id?.message}
                {...register("device_id")}
              />
              <Input
                label="Location UUID"
                placeholder="00000000-0000-0000-0000-000000000000"
                autoComplete="off"
                error={errors.location_id?.message}
                {...register("location_id")}
              />
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                aria-expanded={showAdvanced}
                onClick={() => setShowAdvanced((prev) => !prev)}
              >
                <Filter className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{showAdvanced ? "Hide advanced filters" : "Advanced filters"}</span>
              </Button>
              {activeFilterCount > 0 ? (
                <Badge variant="brand">{activeFilterCount} active filters</Badge>
              ) : null}
              {filters.risk_level ? (
                <Badge variant="info">
                  Filtered by latest risk: {filters.risk_level} (evaluated rows only)
                </Badge>
              ) : null}
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={onReset}
                disabled={isFetching}
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Reset</span>
              </Button>
              <Button type="submit" variant="primary" size="sm" isLoading={isFetching}>
                Apply filters
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
