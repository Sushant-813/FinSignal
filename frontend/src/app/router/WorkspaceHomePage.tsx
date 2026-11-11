import { ArrowRight } from "lucide-react";
import { Link } from "react-router";
import { Alert } from "../../components/ui/Alert.tsx";
import { Badge } from "../../components/ui/Badge.tsx";
import { Button } from "../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card.tsx";
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import { frontendEnv } from "../../lib/api/env.ts";
import { canManageDatasets } from "../../lib/permissions/capabilities.ts";

export function WorkspaceHomePage() {
  const { user } = useAuth();
  const managesDatasets = canManageDatasets(user);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[20px] leading-7 font-semibold tracking-tight text-text-primary">
            Workspace Overview
          </h1>
          <p className="text-sm text-text-secondary">
            Authenticated session and module readiness for your FinSignal workspace.
          </p>
        </div>
        {user ? <Badge variant="brand">{user.role}</Badge> : null}
      </div>

      <Alert variant="info" role="region" aria-label="Workspace phase scope">
        Phase F2 establishes authenticated access, role-aware navigation, and the application shell.
        Operational transaction, analytics, dataset, and investigation views connect in Phases F3
        through F6 without placeholder metrics.
      </Alert>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle size="panel">Signed-In Identity</CardTitle>
            <CardDescription>Verified via GET /api/v1/auth/me (in-memory session)</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-3 text-[13px] sm:grid-cols-2">
              <div>
                <dt className="text-text-muted">Account Email</dt>
                <dd className="mt-0.5 truncate font-medium text-text-primary">
                  {user?.email ?? "Unavailable"}
                </dd>
              </div>
              <div>
                <dt className="text-text-muted">Assigned Role</dt>
                <dd className="mt-0.5 font-medium text-text-primary">{user?.role ?? "Unknown"}</dd>
              </div>
              <div>
                <dt className="text-text-muted">Account Status</dt>
                <dd className="mt-0.5">
                  <Badge variant={user?.is_active ? "success" : "danger"}>
                    {user?.is_active ? "Active" : "Inactive"}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-text-muted">API Base Path</dt>
                <dd className="mt-0.5 font-mono text-xs text-text-secondary">
                  {frontendEnv.apiBaseUrl}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle size="panel">Dataset Access Policy</CardTitle>
            <CardDescription>Capability alignment for your role</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-[13px] text-text-secondary">
            <p>
              Import history viewing: <span className="font-medium text-text-primary">Allowed</span>
            </p>
            <p>
              CSV upload &amp; import recovery:{" "}
              <span className="font-medium text-text-primary">
                {managesDatasets ? "Allowed (Admin / Analyst)" : "Not available for Investigator"}
              </span>
            </p>
          </CardContent>
          <CardFooter>
            <Button asChild variant="secondary" size="sm">
              <Link to="/datasets">
                <span>View dataset workspace</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          </CardFooter>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle size="panel">Upcoming Operational Workspaces</CardTitle>
          <CardDescription>Navigation destinations reserved for Phases F3–F5</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-control border border-border bg-canvas p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary">Transactions</span>
                <Badge variant="neutral">Phase F3</Badge>
              </div>
              <p className="mt-1 text-xs text-text-muted">
                Transaction ledger, exact decimal inspection, and risk analysis.
              </p>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary">Analytics</span>
                <Badge variant="neutral">Phase F3</Badge>
              </div>
              <p className="mt-1 text-xs text-text-muted">
                Volume trends, category spend, and top merchant rankings.
              </p>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary">Investigations</span>
                <Badge variant="neutral">Phase F5</Badge>
              </div>
              <p className="mt-1 text-xs text-text-muted">
                Case queue, assignments, evidence attachment, and AI advisory views.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
