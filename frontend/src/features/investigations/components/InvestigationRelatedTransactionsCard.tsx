import { ArrowUpRight, Link2, Plus } from "lucide-react";
import { Link } from "react-router";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import type { InvestigationTransactionItem } from "../types/investigations.types.ts";

export interface InvestigationRelatedTransactionsCardProps {
  readonly transactions?: InvestigationTransactionItem[] | undefined;
  readonly canLink: boolean;
  readonly onOpenLinkDialog: () => void;
}

export function InvestigationRelatedTransactionsCard({
  transactions = [],
  canLink,
  onOpenLinkDialog,
}: InvestigationRelatedTransactionsCardProps) {
  const relatedCount = transactions.length;

  return (
    <Card elevated className="space-y-4" data-testid="investigation-related-tx-card">
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-brand-600" aria-hidden="true" />
            <CardTitle size="panel">Related Transactions ({relatedCount})</CardTitle>
          </div>
          <CardDescription>
            Financial transactions linked to this investigation case context.
          </CardDescription>
        </div>

        {canLink && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onOpenLinkDialog}
            data-testid="open-link-transaction-button"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            Link Transaction
          </Button>
        )}
      </CardHeader>

      {transactions.length === 0 ? (
        <div className="rounded-card border border-dashed border-border bg-surface-muted/20 p-6 text-center">
          <p className="text-sm text-text-secondary">
            No related transactions have been linked to this investigation.
          </p>
          {canLink && (
            <div className="mt-3">
              <Button type="button" variant="secondary" size="sm" onClick={onOpenLinkDialog}>
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                Link First Transaction
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-card border border-border">
          <Table aria-label="Investigation related transactions table">
            <TableHeader>
              <TableRow>
                <TableHead className="w-28">Type</TableHead>
                <TableHead className="w-36">Transaction ID</TableHead>
                <TableHead className="w-36">Account ID</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead className="w-40">Occurred (UTC)</TableHead>
                <TableHead className="w-40">Linked (UTC)</TableHead>
                <TableHead className="w-24 text-right">Explorer</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((tx) => {
                const isDebit = tx.direction.toUpperCase() === "DEBIT";
                const isPrimary = tx.relationship_type === "PRIMARY";

                return (
                  <TableRow key={tx.transaction_id}>
                    <TableCell>
                      <Badge variant={isPrimary ? "brand" : "neutral"} size="sm">
                        {tx.relationship_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-text-primary">
                      <span title={tx.transaction_id}>{tx.transaction_id.slice(0, 8)}…</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-text-secondary">
                      <span title={tx.account_id}>{tx.account_id.slice(0, 8)}…</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <MoneyValue amount={tx.amount} currency={tx.currency} />
                        <Badge variant={isDebit ? "danger" : "success"} size="sm">
                          {tx.direction}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <TimestampDisplay value={tx.occurred_at} />
                    </TableCell>
                    <TableCell>
                      <TimestampDisplay value={tx.created_at} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        to={`/transactions/${tx.transaction_id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-800 hover:underline"
                        aria-label={`Open transaction ${tx.transaction_id} in explorer`}
                      >
                        View
                        <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </Card>
  );
}
