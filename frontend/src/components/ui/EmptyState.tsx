import { Inbox, SearchX } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type EmptyStateVariant = "empty" | "no-results";

export interface EmptyStateProps {
  title: string;
  description?: string | undefined;
  icon?: ReactNode | undefined;
  action?: ReactNode | undefined;
  variant?: EmptyStateVariant | undefined;
  className?: string | undefined;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  variant = "empty",
  className,
}: EmptyStateProps) {
  const DefaultIcon = variant === "no-results" ? SearchX : Inbox;

  return (
    <div
      data-empty-variant={variant}
      className={cn(
        "flex flex-col items-center justify-center rounded-panel border border-border bg-surface px-6 py-10 text-center",
        className
      )}
    >
      <div
        className="mb-3 flex h-10 w-10 items-center justify-center rounded-control bg-surface-subtle text-text-muted"
        aria-hidden="true"
      >
        {icon ?? <DefaultIcon className="h-5 w-5" />}
      </div>
      <h3 className="text-[15px] leading-[22px] font-semibold text-text-primary">{title}</h3>
      {description ? (
        <p className="mt-1 max-w-md text-[13px] leading-[19px] text-text-secondary">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
