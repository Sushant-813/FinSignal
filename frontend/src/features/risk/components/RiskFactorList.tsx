import { Badge, type BadgeVariant } from "../../../components/ui/Badge.tsx";
import type { RiskFactorDTO, RiskSeverity } from "../types/risk.types.ts";

export interface RiskFactorListProps {
  factors: readonly RiskFactorDTO[];
}

const SEVERITY_VARIANTS: Record<RiskSeverity, BadgeVariant> = {
  INFO: "info",
  LOW: "risk-low",
  MEDIUM: "risk-medium",
  HIGH: "risk-high",
  CRITICAL: "risk-critical",
};

function formatEvidenceValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return "[Unserializable]";
  }
}

export function RiskFactorList({ factors }: RiskFactorListProps) {
  if (factors.length === 0) {
    return (
      <div className="rounded-input border border-border bg-surface-subtle px-4 py-3 text-sm text-text-secondary">
        No triggered risk factors were recorded for this evaluation.
      </div>
    );
  }

  return (
    <ul className="space-y-3" aria-label="Triggered risk factors">
      {factors.map((factor, index) => {
        const evidenceEntries = factor.evidence ? Object.entries(factor.evidence) : [];
        return (
          <li
            key={`${factor.code}-${index}`}
            className="rounded-input border border-border bg-surface-subtle p-3.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={SEVERITY_VARIANTS[factor.severity]} size="sm">
                  {factor.severity}
                </Badge>
                <span className="text-sm font-semibold text-text-primary">{factor.label}</span>
              </div>
              <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-xs text-text-secondary border border-border">
                {factor.code}
              </code>
            </div>

            <p className="mt-1.5 text-sm text-text-secondary">{factor.description}</p>

            {factor.value_numeric || factor.value_text ? (
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-text-muted">
                {factor.value_numeric ? (
                  <span>
                    Numeric signal:{" "}
                    <span className="font-mono font-medium text-text-primary">
                      {factor.value_numeric}
                    </span>
                  </span>
                ) : null}
                {factor.value_text ? (
                  <span>
                    Observed value:{" "}
                    <span className="font-mono font-medium text-text-primary">
                      {factor.value_text}
                    </span>
                  </span>
                ) : null}
              </div>
            ) : null}

            {evidenceEntries.length > 0 ? (
              <dl className="mt-2.5 grid grid-cols-1 gap-x-4 gap-y-1.5 border-t border-border/70 pt-2 sm:grid-cols-2">
                {evidenceEntries.map(([key, val]) => (
                  <div key={key} className="flex items-baseline justify-between gap-2 text-xs">
                    <dt className="font-mono text-text-muted">{key}</dt>
                    <dd
                      className="truncate font-mono text-text-primary"
                      title={formatEvidenceValue(val)}
                    >
                      {formatEvidenceValue(val)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
