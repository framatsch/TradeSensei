/**
 * Dashboard layout — sidebar nav with auth guard.
 * Redirects to /login when no access_token is found in localStorage.
 *
 * Navigation is controlled by AppConfig feature flags:
 *   - enableTaxModule:      shows/hides Steuerbericht
 *   - enableDividendModule: shows/hides Cash & Dividends
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useLogout } from "@/hooks/useAuth";
import { Logo } from "@/components/ui/Logo";
import { AboutModal } from "@/components/ui/AboutModal";
import { AppConfig } from "@/lib/appConfig";

// ─── Nav structure ────────────────────────────────────────────────────────────

interface NavLeaf {
  kind: "leaf";
  href: string;
  label: string;
  icon?: React.ReactNode;
}

interface NavGroup {
  kind: "group";
  label: string;
  defaultOpen?: boolean;
  children: NavLeaf[];
}

interface NavDivider {
  kind: "divider";
}

type NavItem = NavLeaf | NavGroup | NavDivider;

// ─── Icons ────────────────────────────────────────────────────────────────────

const Icons = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  calendar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  analytics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  trades: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
  playbooks: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  tags: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
  import: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  cash: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  tax: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
};

// ─── Build nav items (respects feature flags) ─────────────────────────────────

function buildNavItems(): NavItem[] {
  const items: NavItem[] = [
    // ── Dashboard ─────────────────────────────────────────────────────────────
    {
      kind: "group",
      label: "DASHBOARD",
      defaultOpen: true,
      children: [
        { kind: "leaf", href: "/dashboard", label: "Overview", icon: Icons.dashboard },
        { kind: "leaf", href: "/dashboard/reports/calendar", label: "Calendar", icon: Icons.calendar },
      ],
    },

    // ── Analytics Hub ─────────────────────────────────────────────────────────
    { kind: "leaf", href: "/dashboard/analytics", label: "Analytics", icon: Icons.analytics },

    // ── Trading Log ───────────────────────────────────────────────────────────
    {
      kind: "group",
      label: "TRADING LOG",
      defaultOpen: true,
      children: [
        { kind: "leaf", href: "/dashboard/trades", label: "Trades", icon: Icons.trades },
        { kind: "leaf", href: "/dashboard/playbooks", label: "Playbooks", icon: Icons.playbooks },
        { kind: "leaf", href: "/dashboard/tags", label: "Tags", icon: Icons.tags },
      ],
    },

    // ── System ────────────────────────────────────────────────────────────────
    {
      kind: "group",
      label: "SYSTEM",
      defaultOpen: false,
      children: [
        { kind: "leaf", href: "/dashboard/import", label: "Import", icon: Icons.import },
        { kind: "leaf", href: "/dashboard/settings", label: "Settings", icon: Icons.settings },
      ],
    },
  ];

  // ── Conditionally-enabled modules (hidden unless flag is true) ──────────────
  if (AppConfig.enableDividendModule) {
    (items.find((i) => i.kind === "group" && (i as NavGroup).label === "SYSTEM") as NavGroup | undefined)?.children.unshift(
      { kind: "leaf", href: "/dashboard/cash", label: "Cash & Dividends", icon: Icons.cash }
    );
  }

  if (AppConfig.enableTaxModule) {
    (items.find((i) => i.kind === "group" && (i as NavGroup).label === "SYSTEM") as NavGroup | undefined)?.children.unshift(
      { kind: "leaf", href: "/dashboard/tax", label: "Steuerbericht", icon: Icons.tax }
    );
  }

  return items;
}

const NAV_ITEMS = buildNavItems();

// ─── Sub-components ───────────────────────────────────────────────────────────

function NavLeafItem({
  item,
  pathname,
  indent = false,
  onClick,
}: {
  item: NavLeaf;
  pathname: string;
  indent?: boolean;
  onClick: () => void;
}) {
  const isActive =
    item.href === "/dashboard"
      ? pathname === "/dashboard"
      : pathname.startsWith(item.href);

  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 py-2 text-sm font-medium transition-all duration-200 ${
        indent ? "pl-6 pr-3" : "px-3"
      } ${
        isActive
          ? "nav-active"
          : "rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60"
      }`}
    >
      {item.icon && (
        <span className={`shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`}>
          {item.icon}
        </span>
      )}
      {item.label}
    </Link>
  );
}

function NavGroupItem({
  item,
  pathname,
  onClick,
}: {
  item: NavGroup;
  pathname: string;
  onClick: () => void;
}) {
  const anyChildActive = item.children.some((c) => pathname.startsWith(c.href));
  const [open, setOpen] = useState(item.defaultOpen ?? anyChildActive);

  return (
    <div className="mt-4 first:mt-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-bold tracking-[0.15em] text-muted-foreground hover:text-foreground transition-colors uppercase"
      >
        <span>{item.label}</span>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="mt-0.5 space-y-0.5">
          {item.children.map((child) => (
            <NavLeafItem
              key={child.href}
              item={child}
              pathname={pathname}
              indent
              onClick={onClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

interface Props {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { mutate: logout } = useLogout();
  const hydrate = useAuthStore((s) => s.hydrate);
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !token) {
      router.push("/login");
    }
  }, [hydrated, token, router]);

  const closeSidebar = () => setSidebarOpen(false);

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-30 flex flex-col w-56 bg-sidebar border-r border-border transform transition-transform duration-200 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-3 px-4 py-4 border-b border-border cursor-pointer hover:bg-muted/30 transition-colors group"
          onClick={() => setAboutOpen(true)}
        >
          <Logo size={28} className="group-hover:scale-105 transition-transform duration-200" />
          <span className="font-semibold text-foreground text-sm truncate">Trade Journal</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item, i) => {
            if (item.kind === "group") {
              return (
                <NavGroupItem
                  key={i}
                  item={item}
                  pathname={pathname}
                  onClick={closeSidebar}
                />
              );
            }
            if (item.kind === "leaf") {
              return (
                <NavLeafItem
                  key={item.href}
                  item={item}
                  pathname={pathname}
                  onClick={closeSidebar}
                />
              );
            }
            return null;
          })}
        </nav>

        {/* Help + Sign out */}
        <div className="px-2 py-3 border-t border-border flex flex-col gap-0.5">
          <button
            type="button"
            onClick={() =>
              window.open(
                "/help",
                "tradejournal-help",
                "width=1120,height=760,resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no"
              )
            }
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-5 h-5 shrink-0"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            Help
          </button>
          <button
            onClick={() => logout()}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-5 h-5 shrink-0"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <header className="flex items-center gap-4 px-4 py-3 bg-sidebar border-b border-border lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
            aria-label="Open navigation"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-5 h-5"
            >
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <div
            className="flex items-center gap-2 cursor-pointer hover:bg-muted/30 px-2 py-1 rounded-lg transition-colors"
            onClick={() => setAboutOpen(true)}
          >
            <Logo size={24} />
            <span className="font-semibold text-foreground">Trade Journal</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6 bg-background text-foreground">{children}</main>

        {/* About Modal */}
        <AboutModal
          isOpen={aboutOpen}
          onClose={() => setAboutOpen(false)}
          version={process.env.NEXT_PUBLIC_APP_VERSION}
        />
      </div>
    </div>
  );
}
