import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router";
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import { Sidebar } from "../shell/Sidebar.tsx";
import { TopBar } from "../shell/TopBar.tsx";

export function AppLayout() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const mobileTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  const handleToggleCollapse = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleOpenMobile = useCallback(() => {
    setMobileMenuOpen(true);
  }, []);

  const handleCloseMobile = useCallback(() => {
    setMobileMenuOpen(false);
  }, []);

  return (
    <div className="flex min-h-screen min-w-0 bg-canvas text-text-primary">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-brand-700 focus:shadow-md"
      >
        Skip to main content
      </a>

      <Sidebar
        user={user}
        collapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={handleCloseMobile}
        mobileTriggerRef={mobileTriggerRef}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          mobileOpen={mobileMenuOpen}
          onOpenMobile={handleOpenMobile}
          mobileTriggerRef={mobileTriggerRef}
        />

        <main id="main-content" tabIndex={-1} className="min-w-0 flex-1 p-4 sm:p-5 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
