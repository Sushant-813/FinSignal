import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type {
  HTMLAttributes,
  TableHTMLAttributes,
  TdHTMLAttributes,
  ThHTMLAttributes,
} from "react";
import { cn } from "../../lib/utils/cn.ts";

export function TableContainer({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "w-full overflow-x-auto rounded-panel border border-border bg-surface",
        className
      )}
      {...props}
    />
  );
}

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("w-full border-collapse text-left text-sm", className)} {...props} />;
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("bg-surface-subtle border-b border-border", className)} {...props} />;
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-border bg-surface", className)} {...props} />;
}

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  interactive?: boolean | undefined;
}

export function TableRow({ interactive = false, className, ...props }: TableRowProps) {
  return (
    <tr
      className={cn("h-12 transition-colors", interactive && "hover:bg-surface-hover", className)}
      {...props}
    />
  );
}

export type SortDirection = "asc" | "desc" | "none";

export interface TableHeadProps extends ThHTMLAttributes<HTMLTableCellElement> {
  align?: "left" | "right" | undefined;
  sortDirection?: SortDirection | undefined;
  onSort?: (() => void) | undefined;
}

const ariaSortMap: Record<SortDirection, "ascending" | "descending" | "none"> = {
  asc: "ascending",
  desc: "descending",
  none: "none",
};

export function TableHead({
  align = "left",
  sortDirection,
  onSort,
  scope = "col",
  className,
  children,
  ...props
}: TableHeadProps) {
  const SortIcon =
    sortDirection === "asc" ? ArrowUp : sortDirection === "desc" ? ArrowDown : ArrowUpDown;

  return (
    <th
      scope={scope}
      aria-sort={sortDirection !== undefined ? ariaSortMap[sortDirection] : undefined}
      className={cn(
        "px-4 py-3 text-xs leading-4 font-semibold tracking-wide text-text-secondary whitespace-nowrap",
        align === "right" ? "text-right" : "text-left",
        className
      )}
      {...props}
    >
      {onSort ? (
        <button
          type="button"
          onClick={onSort}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-badge hover:text-text-primary cursor-pointer",
            align === "right" && "flex-row-reverse"
          )}
        >
          <span>{children}</span>
          <SortIcon className="h-3.5 w-3.5 shrink-0 text-text-muted" aria-hidden="true" />
        </button>
      ) : (
        children
      )}
    </th>
  );
}

export interface TableCellProps extends TdHTMLAttributes<HTMLTableCellElement> {
  align?: "left" | "right" | undefined;
  numeric?: boolean | undefined;
}

export function TableCell({
  align,
  numeric = false,
  className,
  children,
  ...props
}: TableCellProps) {
  const effectiveAlign = align ?? (numeric ? "right" : "left");

  return (
    <td
      className={cn(
        "px-4 py-3 text-sm leading-5 text-text-primary align-middle",
        effectiveAlign === "right" ? "text-right" : "text-left",
        numeric && "font-mono tabular-nums whitespace-nowrap",
        className
      )}
      {...props}
    >
      {children}
    </td>
  );
}

export function TableCaption({ className, ...props }: HTMLAttributes<HTMLTableCaptionElement>) {
  return (
    <caption
      className={cn(
        "px-4 py-2.5 text-left text-xs text-text-muted border-t border-border",
        className
      )}
      {...props}
    />
  );
}
