import { ChevronLeft, ChevronRight, ShieldCheck, X } from "lucide-react";
import { useEffect, useRef, type RefObject } from "react";
import { NavLink } from "react-router";
import type { AuthUser } from "../../features/auth/types/auth.types.ts";
import { cn } from "../../lib/utils/cn.ts";
import { getVisibleNavItems } from "./nav-config.ts";

export interface SidebarProps {
  user: AuthUser | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  mobileTriggerRef: RefObject<HTMLButtonElement | null>;
}

export function Sidebar({
  user,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  mobileTriggerRef,
}: SidebarProps) {
  const visibleItems = getVisibleNavItems(user);
  const mobileCloseRef = useRef<HTMLButtonElement>(null);
  const wasMobileOpenRef = useRef(false);

  useEffect(() => {
    if (mobileOpen) {
      wasMobileOpenRef.current = true;
      mobileCloseRef.current?.focus();

      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onCloseMobile();
        }
      };
      document.addEventListener("keydown", handleKeyDown);
      return () => {
        document.removeEventListener("keydown", handleKeyDown);
      };
    }

    if (wasMobileOpenRef.current) {
      wasMobileOpenRef.current = false;
      mobileTriggerRef.current?.focus();
    }
    return undefined;
  }, [mobileOpen, mobileTriggerRef, onCloseMobile]);

  const renderNavLinks = (isCollapsedDesktop: boolean, onItemSelect?: () => void) => (
    <ul className="space-y-1">
      {visibleItems.map((item) => {
        const Icon = item.icon;
        return (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={Boolean(item.end)}
              onClick={onItemSelect}
              aria-label={isCollapsedDesktop ? item.label : undefined}
              title={isCollapsedDesktop ? item.label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded-control px-3 py-2 text-sm transition-colors",
                  isCollapsedDesktop ? "justify-center" : "gap-3",
                  isActive
                    ? "bg-brand-100 font-semibold text-brand-700"
                    : "font-medium text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {isCollapsedDesktop ? (
                <span className="sr-only">{item.label}</span>
              ) : (
                <span>{item.label}</span>
              )}
            </NavLink>
          </li>
        );
      })}
    </ul>
  );

  return (
    <>
      <aside
        aria-label="Sidebar navigation"
        className={cn(
          "hidden shrink-0 border-r border-border bg-surface lg:flex lg:flex-col",
          collapsed ? "w-[68px]" : "w-60"
        )}
      >
        <div
          className={cn(
            "flex h-14 items-center border-b border-border px-3",
            collapsed ? "justify-center" : "justify-between"
          )}
        >
          {collapsed ? null : (
            <div className="flex min-w-0 items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control bg-brand-700 text-text-inverse">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="truncate text-sm font-semibold tracking-tight text-text-primary">
                FinSignal
              </span>
            </div>
          )}

          <button
            type="button"
            onClick={onToggleCollapse}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "Expand navigation sidebar" : "Collapse navigation sidebar"}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-primary"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>

        <nav aria-label="Primary navigation" className="flex-1 p-3">
          {renderNavLinks(collapsed)}
        </nav>
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-overlay" aria-hidden="true" onClick={onCloseMobile} />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Primary navigation"
            className="relative z-10 flex h-full w-64 max-w-[85vw] flex-col border-r border-border bg-surface shadow-lg"
          >
            <div className="flex h-14 items-center justify-between border-b border-border px-4">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-control bg-brand-700 text-text-inverse">
                  <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                </span>
                <span className="text-sm font-semibold tracking-tight text-text-primary">
                  FinSignal
                </span>
              </div>
              <button
                ref={mobileCloseRef}
                type="button"
                onClick={onCloseMobile}
                aria-label="Close navigation menu"
                className="inline-flex h-9 w-9 items-center justify-center rounded-control text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <nav aria-label="Mobile navigation" className="flex-1 overflow-y-auto p-3">
              {renderNavLinks(false, onCloseMobile)}
            </nav>
          </div>
        </div>
      ) : null}
    </>
  );
}
