/**
 * Dashboard layout — sidebar nav with auth guard.
 * Redirects to /login when no access_token is found in localStorage.
 *
 * Navigation is controlled by per-user feature flags:
 *   - tax_report:        shows/hides Cash Report
 *   - cash_and_dividends: shows/hides Cash & Dividends
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
import { useSavedTradeFilters } from "@/hooks/useSavedTradeFilters";
import type { SavedTradeFilterRead } from "@/lib/types";
import { definitionToSearchParams } from "@/lib/tradeFilterUtils";
import FeatureGatedNavItems from "@/components/dashboard/FeatureGatedNavItems";

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

    // ── Analytics Hub — rendered as AnalyticsNavSection in the loop ───────────
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
        { kind: "leaf", href: "/dashboard/import", label: "Import", icon: Icons.import },
      ],
    },
  ];

  // ── Conditionally-enabled modules (hidden unless flag is true) ──────────────
  // Cash & Dividends and Cash Report are per-user feature flags injected
  // by FeatureGatedNavItems, driven by DashboardLayout's useSettings subscription.

  return items;
}

const NAV_ITEMS = buildNavItems();

// ─── Shared class constants ───────────────────────────────────────────────────

/**
 * Section header — static text label, no interactivity.
 * mt-8 on all except the first child (first:mt-0).
 */
const SECTION_HEADER_CLASS =
  "px-4 pt-1 pb-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-slate-500 select-none mt-8 first:mt-0";

/** L1 nav item — inactive */
const L1_INACTIVE =
  "rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60";

/** L2 nav item — inactive */
const L2_INACTIVE =
  "rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60";

// ─── Trades sidebar views ─────────────────────────────────────────────────────

/** Query params that are not part of the filter definition (ignored when diffing). */
const META_PARAMS = new Set(["view_id", "sort_by", "sort_dir", "limit", "cursor"]);

/**
 * Returns true when the current URL filter params differ from the saved view definition.
 * Used to show a "modified" indicator on the active view in the sidebar.
 */
function isViewModified(
  view: SavedTradeFilterRead,
  searchParams: URLSearchParams
): boolean {
  const savedParams = definitionToSearchParams(view.definition);
  const currentParams = new URLSearchParams();
  for (const [k, v] of searchParams.entries()) {
    if (!META_PARAMS.has(k)) currentParams.set(k, v);
  }
  const sortEntries = (p: URLSearchParams) =>
    [...p.entries()].sort(([a], [b]) => a.localeCompare(b));

  return (
    JSON.stringify(sortEntries(savedParams)) !==
    JSON.stringify(sortEntries(currentParams))
  );
}

/**
 * L2 view entry under the Trades accordion.
 * Lock icon = SYSTEM view, User icon = USER view.
 */
function ViewItem({
  view,
  activeViewId,
  isModified,
  onClick,
}: {
  view: SavedTradeFilterRead;
  activeViewId: string | null;
  isModified?: boolean;
  onClick: () => void;
}) {
  const isActive = activeViewId === view.id;

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 pl-[46px] pr-4 py-1.5 text-sm transition-all duration-150 text-left ${
        isActive ? "nav-active font-medium" : L2_INACTIVE
      }`}
    >
      {/* Lock (SYSTEM) or User (USER) icon */}
      <span className={`shrink-0 ${isActive ? "opacity-100" : "opacity-50"}`}>
        {view.scope === "SYSTEM" ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        )}
      </span>

      <span className="truncate flex-1">{view.name}</span>

      {view.needs_review && (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5 shrink-0 text-amber-500">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      )}

      {/* Unsaved-changes indicator — shown when active view filters have been modified */}
      {isActive && isModified && (
        <span
          title="Unsaved changes"
          className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0"
        />
      )}
    </button>
  );
}

/**
 * Special nav item for "Trades" — includes an expand/collapse chevron for
 * the saved-filter views list beneath it.
 */
function TradesNavItem({
  tradeLeaf,
  pathname,
  onClick,
}: {
  tradeLeaf: NavLeaf;
  pathname: string;
  onClick: () => void;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeViewId = searchParams.get("view_id");
  const isOnTradesPage = pathname.startsWith(tradeLeaf.href);

  const [viewsOpen, setViewsOpen] = useState(true);

  const { data: views } = useSavedTradeFilters();
  const sortedViews = [
    ...(views?.filter((v) => v.scope === "SYSTEM") ?? []),
    ...(views?.filter((v) => v.scope === "USER") ?? []),
  ];
  const hasViews = sortedViews.length > 0;

  const isMainActive = isOnTradesPage && !activeViewId;

  const handleMainClick = () => {
    router.push(tradeLeaf.href, { scroll: false });
    onClick();
  };

  const handleViewClick = (view: SavedTradeFilterRead) => {
    const params = definitionToSearchParams(view.definition);
    params.set("view_id", view.id);
    router.push(`${tradeLeaf.href}?${params.toString()}`, { scroll: false });
    onClick();
  };

  return (
    <div>
      {/* "Trades" main row + expand chevron */}
      <div className="flex items-center">
        <button
          onClick={handleMainClick}
          className={`flex flex-1 items-center gap-3 px-4 py-2 text-sm font-normal transition-all duration-150 ${
            isMainActive ? "nav-active" : L1_INACTIVE
          }`}
        >
          <span className={`shrink-0 ${isMainActive ? "opacity-100" : "opacity-50"}`}>
            {tradeLeaf.icon}
          </span>
          {tradeLeaf.label}
        </button>

        {hasViews && (
          <button
            onClick={() => setViewsOpen((o) => !o)}
            aria-label={viewsOpen ? "Collapse views" : "Expand views"}
            className="shrink-0 p-1.5 mr-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={`w-3 h-3 opacity-50 transition-transform ${viewsOpen ? "rotate-180" : ""}`}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        )}
      </div>

      {/* Saved views list */}
      {viewsOpen && hasViews && (
        <div className="mt-1 space-y-0.5">
          {sortedViews.map((view) => (
            <ViewItem
              key={view.id}
              view={view}
              activeViewId={activeViewId}
              isModified={
                view.id === activeViewId &&
                isViewModified(view, searchParams)
              }
              onClick={() => handleViewClick(view)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Analytics sub-tabs ────────────────────────────────────────────────────────

const ANALYTICS_TABS = [
  { id: "time", label: "Time", icon: Icons.clock },
  { id: "strategy", label: "Strategy", icon: Icons.strategy },
  { id: "risk", label: "Risk", icon: Icons.risk },
  { id: "behavior", label: "Behavior", icon: Icons.behavior },
] as const;

/**
 * PERFORMANCE section — static header + L2 sub-tab links.
 * Header does NOT navigate and has no collapse behaviour.
 */
function AnalyticsNavSection({
  pathname,
  onClick,
  showRisk,
}: {
  pathname: string;
  onClick: () => void;
  showRisk: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isOnAnalyticsPage = pathname.startsWith("/dashboard/analytics");

  const activeTab = searchParams.get("tab") ?? "time";

  const handleTabClick = (tabId: string) => {
    router.push(`/dashboard/analytics?tab=${tabId}`, { scroll: false });
    onClick();
  };

  const visibleTabs = ANALYTICS_TABS.filter((t) => t.id !== "risk" || showRisk);

  return (
    <div>
      {/* Static section header */}
      <div className={SECTION_HEADER_CLASS}>Performance</div>

      {/* Sub-tab links */}
      <div className="space-y-0.5">
        {visibleTabs.map((tab) => {
          const isActive = isOnAnalyticsPage && activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`w-full flex items-center gap-2 pl-[46px] pr-4 py-1.5 text-sm font-normal transition-all duration-150 text-left ${
                isActive ? "nav-active" : L2_INACTIVE
              }`}
            >
              <span className={`shrink-0 ${isActive ? "opacity-100" : "opacity-50"}`}>
                {tab.icon}
              </span>
              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

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

/**
 * Section group — static header (no collapse), children always visible.
 */
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
      {/* Static section header */}
      <div className={SECTION_HEADER_CLASS}>{item.label}</div>

      <div className="space-y-0.5">
        {item.children.map((child) => {
          if (child.href === "/dashboard/trades") {
            return (
              <TradesNavItem
                key={child.href}
                tradeLeaf={child}
                pathname={pathname}
                onClick={onClick}
              />
            );
          }
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

  // Per-user feature flags — subscription lives here so FeatureGatedNavItems
  // re-renders immediately when the cache updates (no dynamic/lazy timing issues).
  const { data: settings } = useSettings();
  const features = (settings?.features ?? {}) as Record<string, boolean>;
  const showCash = features["cash_and_dividends"] ?? false;
  const showTax = features["tax_report"] ?? false;
  const showRisk = features["risk_analytics"] ?? false;

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
            if (item.kind === "leaf" && item.href === "/dashboard/analytics") {
              return (
                <AnalyticsNavSection
                  key={item.href}
                  pathname={pathname}
                  onClick={closeSidebar}
                  showRisk={showRisk}
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
          {/* Client-side injected per-user feature nav items (Cash / Tax) */}
          {/* Driven by DashboardLayout's useSettings subscription — no lazy timing window */}
          <FeatureGatedNavItems showCash={showCash} showTax={showTax} />
        </nav>

        {/* Settings + Help + Sign out */}
        <div className="px-2 py-3 border-t border-border flex flex-col gap-0.5">
          <Link
            href="/dashboard/settings"
            onClick={closeSidebar}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-normal transition-colors ${
              pathname.startsWith("/dashboard/settings")
                ? "nav-active"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            }`}
          >
            <span className={`shrink-0 ${pathname.startsWith("/dashboard/settings") ? "opacity-100" : "opacity-50"}`}>
              {Icons.settings}
            </span>
            Settings
          </Link>
          <button
            type="button"
            onClick={() =>
              window.open(
                "/help",
                "tradejournal-help",
                "width=1120,height=760,resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no"
              )
            }
            className="flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-normal text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors"
          >
            <span className="shrink-0 opacity-50">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </span>
            Help
          </button>
          <button
            onClick={() => logout()}
            className="flex items-center gap-3 w-full px-4 py-2 rounded-lg text-sm font-normal text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors"
          >
            <span className="shrink-0 opacity-50">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </span>
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
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
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
