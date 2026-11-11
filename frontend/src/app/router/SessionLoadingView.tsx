import { Loader2 } from "lucide-react";

export interface SessionLoadingViewProps {
  label?: string | undefined;
}

export function SessionLoadingView({ label = "Checking session..." }: SessionLoadingViewProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen items-center justify-center bg-canvas p-6"
    >
      <div className="flex items-center gap-3 rounded-panel border border-border bg-surface px-5 py-3.5 text-sm font-medium text-text-secondary shadow-xs">
        <Loader2 className="h-4 w-4 animate-spin text-brand-700" aria-hidden="true" />
        <span>{label}</span>
      </div>
    </div>
  );
}
