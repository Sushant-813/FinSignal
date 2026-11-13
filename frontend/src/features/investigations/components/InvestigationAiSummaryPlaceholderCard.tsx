import { Sparkles } from "lucide-react";
import { Badge } from "../../../components/ui/Badge.tsx";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";

export function InvestigationAiSummaryPlaceholderCard() {
  return (
    <Card elevated className="space-y-3 opacity-90" data-testid="investigation-ai-summary-placeholder">
      <CardHeader className="flex flex-row items-start justify-between pb-1">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-brand-600" aria-hidden="true" />
          <CardTitle size="panel">AI Case Advisory Summary</CardTitle>
        </div>
        <Badge variant="brand" size="sm">
          Phase F6
        </Badge>
      </CardHeader>
      <CardDescription>
        Automated pattern synthesis and natural-language case briefing will be introduced in Phase F6.
      </CardDescription>
      <div className="rounded-card border border-dashed border-border bg-surface-muted/20 p-4 text-center text-xs text-text-muted">
        AI Case Advisory is scheduled for the upcoming Phase F6 release.
      </div>
    </Card>
  );
}

