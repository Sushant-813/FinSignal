import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type SkeletonVariant = "text" | "text-sm" | "block" | "circle";

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: SkeletonVariant | undefined;
}

const variantClasses: Record<SkeletonVariant, string> = {
  text: "h-4 w-full rounded-badge",
  "text-sm": "h-3.5 w-full rounded-badge",
  block: "h-20 w-full rounded-control",
  circle: "h-9 w-9 rounded-full",
};

export function Skeleton({ variant = "text", className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse bg-surface-subtle", variantClasses[variant], className)}
      {...props}
    />
  );
}

export interface TableSkeletonProps {
  rows?: number | undefined;
  columns?: number | undefined;
  className?: string | undefined;
}

export function TableSkeleton({ rows = 5, columns = 4, className }: TableSkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "w-full rounded-panel border border-border bg-surface p-4 space-y-3",
        className
      )}
    >
      <div
        className="grid gap-3 pb-2 border-b border-border"
        style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: columns }).map((_, colIdx) => (
          <Skeleton key={`hdr-${colIdx}`} variant="text-sm" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={`row-${rowIdx}`}
          className="grid gap-3 py-1.5"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} className="h-4" />
          ))}
        </div>
      ))}
    </div>
  );
}
