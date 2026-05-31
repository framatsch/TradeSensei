/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * Dashboard layout — sidebar nav with auth guard.
 * Redirects to /login when no access_token is found in localStorage.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useLogout } from "@/hooks/useAuth";
import { Logo } from "@/components/ui/Logo";
import { AboutModal } from "@/components/ui/AboutModal";
import { AppConfig } from "@/lib/appConfig";
import { useSettings } from "@/hooks/useSettings";
import { useSavedViews } from "@/hooks/useReportingViews";
import type { SavedDashboardViewRead } from "@/lib/api/types.gen";
import { TopBar } from "@/components/layout/TopBar";
import { useAppContext } from "@/hooks/useAppContext";
import type { AppContext } from "@/stores/appContextStore";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useAccounts } from "@/hooks/useAccounts";
import { EmptyPortfolioGate } from "@/components/layout/EmptyPortfolioGate";
import { useSidebarStore } from "@/stores/sidebarStore";

import { PanelLeftClose, PanelLeftOpen, Filter } from "lucide-react";

// ─── Nav structure ────────────────────────────────────────────────────────────

interface NavLeaf {
  kind: "leaf";
  href: string;
  label: string;
  icon?: React.ReactNode;
  disabled?: boolean;
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
// L1 icons: 18×18px, strokeWidth 1.5
// L2 icons: 14×14px, strokeWidth 1.5

const Icons = {
  // ── Level 1 ─────────────────────────────────────────────────────────────────
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  calendar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  analytics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  trades: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
  playbooks: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  tags: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
  metrics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <line x1="4" y1="21" x2="4" y2="14" />
      <line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" />
      <line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" />
      <line x1="9" y1="8" x2="15" y2="8" />
      <line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  ),
  import: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  cash: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  tax: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),

  // ── Level 2 ─────────────────────────────────────────────────────────────────
  clock: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  strategy: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  risk: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
  behavior: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  ),
};

// ─── Build nav items (respects feature flags and context) ─────────────────────

function buildNavItems(context: AppContext): NavItem[] {
  if (context === "portfolio") {
    return []; // Handled entirely by WorkspaceSidebarNav now
  }
  
  if (context === "library") {
    return [
      {
        kind: "group",
        label: "LIBRARY",
        defaultOpen: true,
        children: [
          { kind: "leaf", href: "/dashboard/library/playbooks", label: "Playbooks", icon: Icons.playbooks },
          { kind: "leaf", href: "/dashboard/library/tags", label: "Tags", icon: Icons.tags },
          { kind: "leaf", href: "/dashboard/library/metrics", label: "Metrics", icon: Icons.metrics },
        ],
      }
    ];
  }
  
  if (context === "checkin") {
    return [
      { kind: "leaf", href: "/dashboard/checkins", label: "Timeline", icon: Icons.clock }
    ];
  }
  
  return [];
}

// ─── Shared class constants ───────────────────────────────────────────────────

const SECTION_HEADER_CLASS =
  "px-4 pt-1 pb-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-slate-500 select-none mt-8 first:mt-0";

const L1_INACTIVE =
  "rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60";

const L2_INACTIVE =
  "rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60";

// ─── Reporting Hub sub-tabs ──────────────────────────────────────────────────

function NavLeafItem({
  item,
  pathname,
  onClick,
}: {
  item: NavLeaf;
  pathname: string;
  onClick: () => void;
}) {
  const isActive =
    item.href === "/dashboard"
      ? pathname === "/dashboard"
      : pathname.startsWith(item.href);

  if (item.disabled) {
    return (
      <div className="flex items-center gap-3 px-4 py-2 text-sm font-normal opacity-50 cursor-not-allowed">
        {item.icon && <span className="shrink-0">{item.icon}</span>}
        {item.label}
      </div>
    );
  }

  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-2 text-sm font-normal transition-all duration-150 ${
        isActive ? "nav-active" : L1_INACTIVE
      }`}
    >
      {item.icon && (
        <span className={`shrink-0 ${isActive ? "opacity-100" : "opacity-50"}`}>
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
  return (
    <div>
      <div className={SECTION_HEADER_CLASS}>{item.label}</div>

      <div className="space-y-0.5">
        {item.children.map((child) => {
          return (
            <NavLeafItem
              key={child.href}
              item={child}
              pathname={pathname}
              onClick={onClick}
            />
          );
        })}
      </div>
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

import { WorkspaceSidebarNav } from "@/components/workspace/WorkspaceSidebarNav";

interface Props {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { desktopSidebarOpen, toggle: toggleDesktopSidebar } = useSidebarStore();
  
  const pathname = usePathname();
  const router = useRouter();
  
  const hydrate = useAuthStore((s) => s.hydrate);
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);

  const { activeContext, setActiveContext } = useAppContext();
  
  // Sync URL to AppContext
  useEffect(() => {
    let expected: AppContext | null = null;
    if (
      pathname === "/dashboard" ||
      pathname.startsWith("/dashboard/workspace") ||
      pathname.startsWith("/dashboard/trades") ||
      pathname.startsWith("/dashboard/reports")
    ) {
      expected = "portfolio";
    } else if (pathname.startsWith("/dashboard/library")) {
      expected = "library";
    } else if (pathname.startsWith("/dashboard/checkins")) {
      expected = "checkin";
    } else if (pathname.startsWith("/dashboard/settings")) {
      expected = "none";
    }

    if (expected && expected !== "none") {
      // Defer to avoid React rendering warnings if triggered during a transition
      setTimeout(() => setActiveContext(expected!), 0);
    }
  }, [pathname, setActiveContext]);

  const { portfolios, activePortfolioId, isLoading: isPortfolioLoading, isError: isPortfolioError } = useActivePortfolio();
  
  const { data: accounts, isLoading: isAccountsLoading } = useAccounts(activePortfolioId || undefined);

  const hideGlobalSidebar = pathname.startsWith("/dashboard/checkins") || pathname.startsWith("/dashboard/settings") || pathname.startsWith("/dashboard/trades");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleDesktopSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const { data: settings } = useSettings();
  const features = (settings?.features ?? {}) as Record<string, boolean>;
  const showRisk = features["risk_analytics"] ?? false;
  const showReporting = features["reporting_hub"] ?? false;

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !token) {
      router.push("/login");
    }
  }, [hydrated, token, router]);

  const closeSidebar = () => setSidebarOpen(false);

  if (!hydrated || !token) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const NAV_ITEMS = buildNavItems(activeContext);

  const renderContent = () => {
    if (activeContext === 'portfolio' && !pathname.startsWith("/dashboard/settings")) {
      if (isPortfolioError) {
        return (
          <div className="flex items-center justify-center h-full">
            <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md">
              Failed to load portfolios — please refresh
            </div>
          </div>
        );
      }
      if (isPortfolioLoading || isAccountsLoading) {
        return (
          <div className="flex items-center justify-center h-full">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        );
      }
      
      const missing = portfolios.length === 0 ? "portfolio" : (accounts?.length === 0 ? "account" : null);

      if (missing && !pathname.startsWith("/dashboard/trades") && !pathname.startsWith("/dashboard/settings")) {
        return <EmptyPortfolioGate missing={missing} />;
      }
    }
    return children;
  };

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden" style={{ "--topbar-height": "3.5rem" } as React.CSSProperties}>
      <TopBar 
        onToggleMobileSidebar={() => setSidebarOpen(!sidebarOpen)}
        onToggleDesktopSidebar={toggleDesktopSidebar}
        isMobileSidebarOpen={sidebarOpen}
        isDesktopSidebarOpen={desktopSidebarOpen}
      />
      
      <div className="flex flex-1 overflow-hidden relative">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/60 lg:hidden"
            onClick={closeSidebar}
          />
        )}

        {/* Sidebar */}
        {!hideGlobalSidebar && (
          <aside
            className={`fixed lg:static top-[var(--topbar-height)] bottom-0 left-0 z-30 flex flex-col bg-sidebar border-border transition-all duration-300 ease-in-out overflow-hidden shrink-0 ${
              sidebarOpen ? "translate-x-0 w-56 border-r" : "-translate-x-full w-56 lg:translate-x-0"
            } ${
              desktopSidebarOpen
                ? "lg:w-56 lg:border-r lg:opacity-100 lg:visible"
                : "lg:w-0 lg:border-r-0 lg:opacity-0 lg:invisible"
            }`}
          >
            <div className="w-56 h-full flex flex-col">
              {/* Nav */}
              <nav className="flex-1 py-3 overflow-y-auto">
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
                {/* Render the new workspace nav directly for the portfolio context */}
                {activeContext === 'portfolio' && (
                  <WorkspaceSidebarNav />
                )}

              </nav>
            </div>
          </aside>
        )}

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          <main className={`flex-1 overflow-y-auto bg-background text-foreground ${hideGlobalSidebar ? "" : "p-6 pt-14"}`}>
            {renderContent()}
          </main>
        </div>
      </div>
    </div>
  );
}
