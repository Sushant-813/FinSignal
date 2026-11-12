import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils/cn.ts";
import { Button } from "./Button.tsx";
import { Select } from "./Select.tsx";

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (nextPage: number) => void;
  onPageSizeChange?: ((nextPageSize: number) => void) | undefined;
  pageSizeOptions?: readonly number[] | undefined;
  disabled?: boolean | undefined;
  ariaLabel?: string | undefined;
  className?: string | undefined;
}

const DEFAULT_PAGE_SIZES = [25, 50, 100] as const;

export function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZES,
  disabled = false,
  ariaLabel = "Pagination",
  className,
}: PaginationProps) {
  const safeTotalPages = Math.max(0, totalPages);
  const canGoPrev = !disabled && page > 1;
  const canGoNext = !disabled && safeTotalPages > 0 && page < safeTotalPages;

  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = total === 0 ? 0 : Math.min(page * pageSize, total);

  return (
    <nav
      aria-label={ariaLabel}
      className={cn(
        "flex flex-col gap-3 rounded-panel border border-border bg-surface px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between",
        className
      )}
    >
      <div className="text-[13px] text-text-secondary tabular-nums">
        {total === 0 ? (
          <span>0 results</span>
        ) : startItem <= total ? (
          <span>
            Showing <span className="font-medium text-text-primary">{startItem}</span>–
            <span className="font-medium text-text-primary">{endItem}</span> of{" "}
            <span className="font-medium text-text-primary">{total}</span> results
          </span>
        ) : (
          <span>
            Page <span className="font-medium text-text-primary">{page}</span> (out of range;{" "}
            <span className="font-medium text-text-primary">{total}</span> total results)
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {onPageSizeChange ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Rows</span>
            <Select
              label="Rows per page"
              hideLabel
              value={String(pageSize)}
              disabled={disabled}
              onValueChange={(val) => {
                const parsed = Number.parseInt(val, 10);
                if (Number.isInteger(parsed) && parsed > 0) {
                  onPageSizeChange(parsed);
                }
              }}
              options={pageSizeOptions.map((size) => ({
                value: String(size),
                label: String(size),
              }))}
              containerClassName="w-20"
            />
          </div>
        ) : null}

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={!canGoPrev}
            onClick={() => onPageChange(page - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            <span>Previous</span>
          </Button>

          <span className="px-2 text-[13px] font-medium text-text-primary tabular-nums">
            Page {page} of {Math.max(1, safeTotalPages)}
          </span>

          <Button
            variant="secondary"
            size="sm"
            disabled={!canGoNext}
            onClick={() => onPageChange(page + 1)}
            aria-label="Next page"
          >
            <span>Next</span>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
