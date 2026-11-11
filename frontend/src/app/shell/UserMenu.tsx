import { ChevronDown, LogOut, UserCircle2 } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Badge, type BadgeVariant } from "../../components/ui/Badge.tsx";
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import type { UserRole } from "../../features/auth/types/auth.types.ts";

function getRoleBadgeVariant(role: UserRole): BadgeVariant {
  if (role === "ADMIN") {
    return "brand";
  }
  if (role === "ANALYST") {
    return "info";
  }
  return "neutral";
}

export function UserMenu() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenuOpen(false);
        triggerRef.current?.focus();
      }
    };

    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [menuOpen]);

  if (!user) {
    return null;
  }

  const handleSignOut = () => {
    setMenuOpen(false);
    signOut();
    void navigate("/login", { replace: true });
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setMenuOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        aria-controls={menuOpen ? menuId : undefined}
        className="flex h-9 items-center gap-2 rounded-control border border-border bg-surface px-2.5 text-sm text-text-primary transition-colors hover:bg-surface-hover"
      >
        <UserCircle2 className="h-4 w-4 shrink-0 text-text-secondary" aria-hidden="true" />
        <span className="max-w-[140px] truncate text-[13px] font-medium sm:max-w-[200px]">
          {user.email}
        </span>
        <Badge variant={getRoleBadgeVariant(user.role)} className="hidden sm:inline-flex">
          {user.role}
        </Badge>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-text-muted" aria-hidden="true" />
      </button>

      {menuOpen ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Account menu"
          className="absolute right-0 z-40 mt-2 w-64 rounded-panel border border-border bg-surface p-2 shadow-lg"
        >
          <div className="space-y-1.5 border-b border-border px-2.5 py-2">
            <p className="truncate text-[13px] font-semibold text-text-primary">{user.email}</p>
            <div className="flex items-center gap-2">
              <Badge variant={getRoleBadgeVariant(user.role)}>{user.role}</Badge>
              <span className="text-xs text-text-muted">Active session</span>
            </div>
          </div>

          <div className="pt-1.5">
            <button
              type="button"
              role="menuitem"
              onClick={handleSignOut}
              className="flex w-full items-center gap-2 rounded-control px-2.5 py-2 text-left text-[13px] font-medium text-danger transition-colors hover:bg-tint-danger"
            >
              <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
