import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import type { TransactionDetailResponse } from "../types/transactions.types.ts";

export interface TransactionFactsCardProps {
  transaction: TransactionDetailResponse;
}

export function TransactionFactsCard({ transaction }: TransactionFactsCardProps) {
  return (
    <Card as="section" aria-labelledby="tx-facts-heading">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle id="tx-facts-heading" as="h2" size="section">
              Immutable Transaction Facts
            </CardTitle>
            <CardDescription className="mt-1">
              Canonical ledger record as ingested. Facts are authoritative and never altered by risk
              evaluations.
            </CardDescription>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xs text-text-muted">Amount</div>
            <MoneyValue
              amount={transaction.amount}
              currency={transaction.currency}
              className="text-xl font-semibold text-text-primary"
            />
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-xs text-text-muted">External Transaction ID</dt>
            <dd className="mt-0.5 font-mono text-sm font-medium break-all text-text-primary">
              {transaction.external_transaction_id}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Internal UUID</dt>
            <dd className="mt-0.5 font-mono text-xs break-all text-text-secondary">
              {transaction.id}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Source Namespace</dt>
            <dd className="mt-0.5 font-mono text-sm text-text-primary">
              {transaction.source_namespace}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Direction</dt>
            <dd className="mt-1">
              <Badge variant={transaction.direction === "DEBIT" ? "warning" : "success"} size="sm">
                {transaction.direction}
              </Badge>
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Transaction Type</dt>
            <dd className="mt-0.5 text-sm text-text-primary">{transaction.transaction_type}</dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Category</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              {transaction.category ?? <span className="text-text-muted">—</span>}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Payment Method</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              {transaction.payment_method ?? <span className="text-text-muted">—</span>}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Channel</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              {transaction.channel ?? <span className="text-text-muted">—</span>}
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Occurred At</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              <TimestampDisplay value={transaction.occurred_at} timeZone="UTC" />
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">Ingested Created At</dt>
            <dd className="mt-0.5 text-sm text-text-primary">
              <TimestampDisplay value={transaction.created_at} timeZone="UTC" />
            </dd>
          </div>

          <div>
            <dt className="text-xs text-text-muted">First Seen Import ID</dt>
            <dd className="mt-0.5 font-mono text-xs break-all text-text-secondary">
              {transaction.first_seen_import_id ?? <span className="text-text-muted">—</span>}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
