import { formatTimestamp } from "../../lib/formatting/datetime.ts";
import { cn } from "../../lib/utils/cn.ts";

export interface TimestampDisplayProps {
  value: string | null | undefined;
  timeZone?: string | undefined;
  includeSeconds?: boolean | undefined;
  emptyLabel?: string | undefined;
  className?: string | undefined;
}

export function TimestampDisplay({
  value,
  timeZone = "UTC",
  includeSeconds = true,
  emptyLabel = "—",
  className,
}: TimestampDisplayProps) {
  if (!value || value.trim() === "") {
    return (
      <span className={cn("text-text-muted", className)} aria-label="Unavailable">
        {emptyLabel}
      </span>
    );
  }

  const formatted = formatTimestamp(value, timeZone, { includeSeconds });
  if (formatted === "Invalid timestamp") {
    return (
      <span className={cn("text-text-muted", className)} title={value}>
        Invalid timestamp
      </span>
    );
  }

  return (
    <time
      dateTime={value}
      title={`Raw ISO: ${value}`}
      className={cn("font-mono tabular-nums whitespace-nowrap", className)}
    >
      {formatted}
    </time>
  );
}
