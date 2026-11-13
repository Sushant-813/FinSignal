import {
  ArrowLeftRight,
  BarChart3,
  Database,
  FolderSearch,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";
import type { AuthUser } from "../../features/auth/types/auth.types.ts";
import {
  canAccessWorkspace,
  canViewAnalytics,
  canViewDatasetImports,
  canViewInvestigations,
  canViewTransactions,
} from "../../lib/permissions/capabilities.ts";

export interface NavItem {
  readonly to: string;
  readonly label: string;
  readonly end?: boolean | undefined;
  readonly icon: LucideIcon;
  readonly isVisible: (user: AuthUser | null) => boolean;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    to: "/",
    label: "Dashboard Overview",
    end: true,
    icon: LayoutDashboard,
    isVisible: canAccessWorkspace,
  },
  {
    to: "/transactions",
    label: "Transactions",
    icon: ArrowLeftRight,
    isVisible: canViewTransactions,
  },
  {
    to: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    isVisible: canViewAnalytics,
  },
  {
    to: "/investigations",
    label: "Investigations",
    icon: FolderSearch,
    isVisible: canViewInvestigations,
  },
  {
    to: "/datasets",
    label: "Datasets",
    icon: Database,
    isVisible: canViewDatasetImports,
  },
];

export function getVisibleNavItems(user: AuthUser | null): readonly NavItem[] {
  return NAV_ITEMS.filter((item) => item.isVisible(user));
}

const ROUTE_TITLES: Readonly<Record<string, string>> = {
  "/": "Dashboard Overview",
  "/transactions": "Transactions",
  "/analytics": "Analytics",
  "/investigations": "Investigations",
  "/datasets": "Datasets",
};

export function getRouteBreadcrumbLabel(pathname: string): string {
  const direct = ROUTE_TITLES[pathname];
  if (direct) {
    return direct;
  }
  if (pathname.startsWith("/transactions/")) {
    return "Transaction Detail";
  }
  if (pathname.startsWith("/investigations/")) {
    return "Investigation Workspace";
  }
  if (pathname.startsWith("/datasets/imports/")) {
    return "Dataset Import Details";
  }
  const matched = NAV_ITEMS.find((item) => item.to !== "/" && pathname.startsWith(item.to));
  return matched ? matched.label : "Workspace";
}
