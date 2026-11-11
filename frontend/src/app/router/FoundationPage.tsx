import { Badge } from "../../components/ui/Badge.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card.tsx";
import { frontendEnv } from "../../lib/api/env.ts";

export function FoundationPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-4 sm:p-6 lg:p-8">
      <Card
        as="section"
        aria-label="FinSignal foundation"
        className="w-full max-w-2xl"
        padding="lg"
      >
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle as="h1" size="page">
              FinSignal
            </CardTitle>
            <Badge variant="brand">Phase F1 Foundation</Badge>
          </div>
          <CardDescription>
            Financial Transaction Intelligence &amp; Investigation Platform — Application foundation
            and design system baseline.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-3 rounded-control border border-border bg-surface-subtle p-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-text-muted">Environment</dt>
              <dd className="mt-0.5 font-mono text-[13px] text-text-primary">
                {frontendEnv.appEnv}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-text-muted">API Base Path</dt>
              <dd className="mt-0.5 font-mono text-[13px] text-text-primary">
                {frontendEnv.apiBaseUrl}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </main>
  );
}
