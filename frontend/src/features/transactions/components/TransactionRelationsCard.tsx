import { Link } from "react-router";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import type { TransactionDetailResponse } from "../types/transactions.types.ts";

export interface TransactionRelationsCardProps {
  transaction: TransactionDetailResponse;
}

function buildFilteredTransactionsUrl(
  namespace: string,
  extraParam: Record<string, string>
): string {
  const params = new URLSearchParams({ source_namespace: namespace, ...extraParam });
  return `/transactions?${params.toString()}`;
}

export function TransactionRelationsCard({ transaction }: TransactionRelationsCardProps) {
  const ns = transaction.source_namespace;

  return (
    <Card as="section" aria-labelledby="tx-relations-heading">
      <CardHeader>
        <CardTitle id="tx-relations-heading" as="h2" size="section">
          Relational Entity Context
        </CardTitle>
        <CardDescription>
          Linked account, counterparty, merchant, device, and geographic metadata recorded on the
          transaction.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-input border border-border bg-surface-subtle p-3.5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
                Primary Account
              </h3>
              <Link
                to={buildFilteredTransactionsUrl(ns, { account_id: transaction.account.id })}
                className="text-xs font-medium text-brand-700 hover:underline"
              >
                Filter account txns
              </Link>
            </div>
            <dl className="mt-2 space-y-1 text-xs">
              <div className="flex justify-between gap-2">
                <dt className="text-text-muted">External ID</dt>
                <dd className="font-mono text-text-primary">
                  {transaction.account.external_account_id ?? "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-text-muted">Type / Status</dt>
                <dd className="text-text-primary">
                  {transaction.account.account_type} · {transaction.account.status}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-text-muted">UUID</dt>
                <dd
                  className="truncate font-mono text-text-secondary"
                  title={transaction.account.id}
                >
                  {transaction.account.id}
                </dd>
              </div>
            </dl>
          </div>

          <div className="rounded-input border border-border bg-surface-subtle p-3.5">
            <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
              Counterparty Account
            </h3>
            {transaction.counterparty_account ? (
              <dl className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">External ID</dt>
                  <dd className="font-mono text-text-primary">
                    {transaction.counterparty_account.external_account_id ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">Type / Status</dt>
                  <dd className="text-text-primary">
                    {transaction.counterparty_account.account_type} ·{" "}
                    {transaction.counterparty_account.status}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">UUID</dt>
                  <dd
                    className="truncate font-mono text-text-secondary"
                    title={transaction.counterparty_account.id}
                  >
                    {transaction.counterparty_account.id}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-2 text-xs text-text-muted">Not recorded</p>
            )}
          </div>

          <div className="rounded-input border border-border bg-surface-subtle p-3.5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
                Merchant
              </h3>
              {transaction.merchant ? (
                <Link
                  to={buildFilteredTransactionsUrl(ns, { merchant_id: transaction.merchant.id })}
                  className="text-xs font-medium text-brand-700 hover:underline"
                >
                  Filter merchant txns
                </Link>
              ) : null}
            </div>
            {transaction.merchant ? (
              <dl className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">Name</dt>
                  <dd className="font-medium text-text-primary">
                    {transaction.merchant.merchant_name}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">Category</dt>
                  <dd className="text-text-primary">{transaction.merchant.merchant_category}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-text-muted">External ID</dt>
                  <dd className="font-mono text-text-secondary">
                    {transaction.merchant.external_merchant_id ?? "—"}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-2 text-xs text-text-muted">Not recorded</p>
            )}
          </div>

          <div className="rounded-input border border-border bg-surface-subtle p-3.5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
                Device & Location
              </h3>
              <div className="flex gap-3">
                {transaction.device ? (
                  <Link
                    to={buildFilteredTransactionsUrl(ns, { device_id: transaction.device.id })}
                    className="text-xs font-medium text-brand-700 hover:underline"
                  >
                    Filter device
                  </Link>
                ) : null}
                {transaction.location ? (
                  <Link
                    to={buildFilteredTransactionsUrl(ns, { location_id: transaction.location.id })}
                    className="text-xs font-medium text-brand-700 hover:underline"
                  >
                    Filter location
                  </Link>
                ) : null}
              </div>
            </div>
            <dl className="mt-2 space-y-1 text-xs">
              <div className="flex justify-between gap-2">
                <dt className="text-text-muted">Device</dt>
                <dd className="font-mono text-text-primary">
                  {transaction.device
                    ? `${transaction.device.device_type ?? "Unknown type"} (${transaction.device.external_device_id ?? transaction.device.id})`
                    : "Not recorded"}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-text-muted">Location</dt>
                <dd className="text-text-primary">
                  {transaction.location
                    ? [
                        transaction.location.city,
                        transaction.location.state,
                        transaction.location.country,
                      ]
                        .filter(Boolean)
                        .join(", ")
                    : "Not recorded"}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
