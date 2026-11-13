import { ArrowUpRight, CreditCard } from "lucide-react";
import { Link } from "react-router";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import type { InvestigationPrimaryTransactionDTO } from "../types/investigations.types.ts";

export interface InvestigationPrimaryTransactionCardProps {
  readonly transaction: InvestigationPrimaryTransactionDTO;
}

export function InvestigationPrimaryTransactionCard({
  transaction,
}: InvestigationPrimaryTransactionCardProps) {
  const isDebit = transaction.direction.toUpperCase() === "DEBIT";

  return (
    <Card elevated className="space-y-4" data-testid="investigation-primary-tx-card">
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-brand-600" aria-hidden="true" />
            <CardTitle size="panel">Primary Transaction Facts</CardTitle>
          </div>
          <CardDescription>
            Authoritative financial transaction triggering this investigation.
          </CardDescription>
        </div>
        <Link
          to={`/transactions/${transaction.id}`}
          className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-800 hover:underline"
          aria-label="View transaction in transaction explorer"
        >
          View Explorer
          <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </CardHeader>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Monetary Amount */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">Amount</p>
          <div className="mt-1 flex items-baseline gap-2">
            <MoneyValue
              amount={transaction.amount}
              currency={transaction.currency}
              className="text-lg font-semibold text-text-primary"
            />
            <Badge variant={isDebit ? "danger" : "success"} size="sm">
              {transaction.direction}
            </Badge>
          </div>
        </div>

        {/* External ID */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">External ID</p>
          <p className="mt-1 font-mono text-sm font-medium text-text-primary">
            {transaction.external_transaction_id}
          </p>
        </div>

        {/* Timestamp */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">Occurred At (UTC)</p>
          <div className="mt-1 text-sm font-medium text-text-primary">
            <TimestampDisplay value={transaction.occurred_at} />
          </div>
        </div>

        {/* Account ID */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">Account ID</p>
          <p className="mt-1 font-mono text-xs text-text-primary" title={transaction.account_id}>
            {transaction.account_id}
          </p>
        </div>

        {/* Namespace */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">Namespace</p>
          <p className="mt-1 font-mono text-xs font-medium text-text-primary">
            {transaction.source_namespace}
          </p>
        </div>

        {/* Category & Payment Method */}
        <div className="rounded-card border border-border bg-surface-muted/30 p-3">
          <p className="text-xs font-medium text-text-secondary">Category / Method</p>
          <p className="mt-1 text-sm text-text-primary">
            {transaction.category || "Uncategorized"}
            {transaction.payment_method ? ` (${transaction.payment_method})` : ""}
          </p>
        </div>
      </div>
    </Card>
  );
}
