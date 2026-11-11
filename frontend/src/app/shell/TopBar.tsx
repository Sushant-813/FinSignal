import { Menu } from "lucide-react";
import type { RefObject } from "react";
import { useLocation } from "react-router";
import { getRouteBreadcrumbLabel } from "./nav-config.ts";
import { UserMenu } from "./UserMenu.tsx";

export interface TopBarProps {
  mobileOpen: boolean;
  onOpenMobile: () => void;
  mobileTriggerRef: RefObject<HTMLButtonElement | null>;
}

export function TopBar({ mobileOpen, onOpenMobile, mobileTriggerRef }: TopBarProps) {
  const { pathname } = useLocation();
  const currentLabel = getRouteBreadcrumbLabel(pathname);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-surface px-4 sm:px-5 lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          ref={mobileTriggerRef}
          type="button"
          onClick={onOpenMobile}
          aria-expanded={mobileOpen}
          aria-label="Open navigation menu"
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-control border border-border bg-surface text-text-primary transition-colors hover:bg-surface-hover lg:hidden"
        >
          <Menu className="h-4 w-4" aria-hidden="true" />
        </button>

        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex items-center gap-1.5 text-[13px]">
            <li className="hidden text-text-muted sm:inline">FinSignal</li>
            <li aria-hidden="true" className="hidden text-text-muted sm:inline">
              /
            </li>
            <li aria-current="page" className="truncate font-semibold text-text-primary">
              {currentLabel}
            </li>
          </ol>
        </nav>
      </div>

      <UserMenu />
    </header>
  );
}
