import { FileText } from "lucide-react";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Card, CardDescription, CardHeader, CardTitle } from "../../../components/ui/Card.tsx";

export function InvestigationEvidencePlaceholderCard() {
  return (
    <Card
      elevated
      className="space-y-3 opacity-90"
      data-testid="investigation-evidence-placeholder"
    >
      <CardHeader className="flex flex-row items-start justify-between pb-1">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-text-muted" aria-hidden="true" />
          <CardTitle size="panel">Evidence & Attachments</CardTitle>
        </div>
        <Badge variant="neutral" size="sm">
          Phase F6
        </Badge>
      </CardHeader>
      <CardDescription>
        File evidence attachment, chain-of-custody tracking, and artifact notes will be available in
        Phase F6.
      </CardDescription>
      <div className="rounded-card border border-dashed border-border bg-surface-muted/20 p-4 text-center text-xs text-text-muted">
        Evidence management is scheduled for the upcoming Phase F6 release.
      </div>
    </Card>
  );
}
