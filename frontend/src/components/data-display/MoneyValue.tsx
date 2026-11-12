import { formatMoneyParts, isValidDecimalString } from "../../lib/formatting/money.ts";
import { cn } from "../../lib/utils/cn.ts";

export interface MoneyValueProps {
  amount: string | null | undefined;
  currency?: string | null | undefined;
  emptyLabel?: string | undefined;
  className?: string | undefined;
  currencyClassName?: string | undefined;
}

export function MoneyValue({
  amount,
  currency,
  emptyLabel = "—",
  className,
  currencyClassName,
}: MoneyValueProps) {
  if (amount === null || amount === undefined || amount.trim() === "") {
    return (
      <span
        className={cn("font-mono tabular-nums text-text-muted", className)}
        aria-label="Unavailable"
      >
        {emptyLabel}
      </span>
    );
  }

  if (!isValidDecimalString(amount)) {
    return (
      <span className={cn("text-text-muted", className)} aria-label="Invalid monetary value">
        Unavailable
      </span>
    );
  }

  let parts;
  try {
    parts = formatMoneyParts(amount, currency);
  } catch {
    return (
      <span className={cn("text-text-muted", className)} aria-label="Invalid monetary value">
        Unavailable
      </span>
    );
  }

  if (!parts) {
    return (
      <span
        className={cn("font-mono tabular-nums text-text-muted", className)}
        aria-label="Unavailable"
      >
        {emptyLabel}
      </span>
    );
  }

  return (
    <span
      className={cn("inline-flex flex-wrap items-baseline gap-1 font-mono tabular-nums", className)}
    >
      <span>{parts.amount}</span>
      {parts.currency ? (
        <span className={cn("text-xs font-medium text-text-muted", currencyClassName)}>
          {parts.currency}
        </span>
      ) : null}
    </span>
  );
}
