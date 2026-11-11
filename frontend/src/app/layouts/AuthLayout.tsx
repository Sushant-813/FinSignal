import { ShieldCheck } from "lucide-react";
import { Outlet } from "react-router";

export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-8 sm:px-6">
      <div className="w-full max-w-md space-y-6">
        <header className="flex items-center justify-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-control bg-brand-700 text-text-inverse shadow-xs">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="text-left">
            <span className="block text-base font-semibold tracking-tight text-text-primary">
              FinSignal
            </span>
            <span className="block text-xs text-text-muted">
              Transaction Intelligence &amp; Investigation
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
