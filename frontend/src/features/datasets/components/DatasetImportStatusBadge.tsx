import { Loader2 } from "lucide-react";
import { Badge } from "../../../components/ui/Badge.tsx";
import type { DatasetImportStatus } from "../types/datasets.types.ts";

export interface DatasetImportStatusBadgeProps {
  status: DatasetImportStatus | string;
  className?: string | undefined;
}

export function DatasetImportStatusBadge({ status, className }: DatasetImportStatusBadgeProps) {
  const normStatus = (status || "").toUpperCase();

  switch (normStatus) {
    case "COMPLETED":
      return (
        <Badge variant="success" className={className}>
          Completed
        </Badge>
      );
    case "PROCESSING":
      return (
        <Badge variant="info" className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          Processing
        </Badge>
      );
    case "PENDING":
      return (
        <Badge variant="warning" className={className}>
          Pending
        </Badge>
      );
    case "FAILED":
      return (
        <Badge variant="danger" className={className}>
          Failed
        </Badge>
      );
    default:
      return (
        <Badge variant="neutral" className={className}>
          {status}
        </Badge>
      );
  }
}

