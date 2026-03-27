"use client";

/**
 * Analytics Hub — /dashboard/analytics
 *
 * Top-level page that hosts four analysis tabs:
 *   - Time     → TimeAnalysisTab  (hourly / weekday / monthly / yearly)
 *   - Strategy → StrategyAnalysisTab (playbook performance)
 *   - Risk     → RiskMetricsTab   (R-multiple + drawdown)
 *   - Behavior → BehaviorAnalysisTab (tag analysis)
 *
 * The active tab is persisted in the `?tab=` URL search param.
 * Account filtering lives at page level and is passed to tabs that need it.
 */

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BarChart2, Clock, BookOpen, TrendingDown, Tag } from "lucide-react";

import { useReportData } from "@/hooks/useReportData";
import { PageHeader } from "@/components/ui/PageHeader";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { Spinner } from "@/components/ui/Spinner";
import { TimeAnalysisTab } from "./TimeAnalysisTab";
import { StrategyAnalysisTab } from "./StrategyAnalysisTab";
import { RiskMetricsTab } from "./RiskMetricsTab";
import { BehaviorAnalysisTab } from "./BehaviorAnalysisTab";

// ─── Tab config ───────────────────────────────────────────────────────────────

type TabId = "time" | "strategy" | "risk" | "behavior";

interface TabConfig {
  id: TabId;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const TABS: TabConfig[] = [
  {
    id: "time",
    label: "Time",
    icon: <Clock className="w-4 h-4" />,
    description: "Hourly, weekday, monthly & yearly breakdown",
  },
  {
    id: "strategy",
    label: "Strategy",
    icon: <BookOpen className="w-4 h-4" />,
    description: "Playbook performance comparison",
  },
  {
    id: "risk",
    label: "Risk",
    icon: <TrendingDown className="w-4 h-4" />,
    description: "R-multiple distribution & drawdown stats",
  },
  {
    id: "behavior",
    label: "Behavior",
    icon: <Tag className="w-4 h-4" />,
    description: "Tag frequency & error pattern analysis",
  },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function AnalyticsHubPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Resolve active tab from URL, default to "time"
  const rawTab = searchParams.get("tab");
  const activeTab: TabId =
    rawTab === "strategy" || rawTab === "risk" || rawTab === "behavior"
      ? rawTab
      : "time";

  // Account filter state — only used by Time tab; others use all trades
  const [accountId, setAccountId] = useState<string | null>(null);

  // Fetch all report data once at page level
  const { trades, getAggregated, isLoading, isError } =
    useReportData(accountId);

  // Change tab by updating URL param (keeps browser history navigable)
  const handleTabChange = useCallback(
    (tab: TabId) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", tab);
      router.push(`/dashboard/analytics?${params.toString()}`);
    },
    [router, searchParams]
  );

  return (
    <div className="flex flex-col gap-6 pb-12">
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <PageHeader
        title="Analytics Hub"
        subtitle="Deep-dive into your trading performance across time, strategy, risk, and behavior."
      >
        {/* Account filter shown in header only for the Time tab */}
        {activeTab === "time" && (
          <AccountFilter value={accountId} onChange={setAccountId} />
        )}
      </PageHeader>

      {/* ── Tab bar ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-1 rounded-xl border border-border bg-muted/30 p-1 self-start">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              aria-selected={isActive}
              role="tab"
              className={[
                "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
              ].join(" ")}
            >
              {tab.icon}
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── Active tab subtitle ───────────────────────────────────────────── */}
      {TABS.find((t) => t.id === activeTab) && (
        <p className="text-xs text-muted-foreground -mt-4">
          {TABS.find((t) => t.id === activeTab)!.description}
        </p>
      )}

      {/* ── Error state ──────────────────────────────────────────────────── */}
      {isError && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-600 dark:text-rose-400 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 shrink-0" />
          <span>
            Failed to load trade data. Please refresh or try again later.
          </span>
        </div>
      )}

      {/* ── Loading overlay (full-page spinner before any data is available) */}
      {isLoading && trades.length === 0 ? (
        <div className="flex items-center justify-center py-32">
          <Spinner size="lg" />
        </div>
      ) : (
        /* ── Tab content ─────────────────────────────────────────────────── */
        <div role="tabpanel" className="min-h-[400px]">
          {activeTab === "time" && (
            <TimeAnalysisTab
              trades={trades}
              isLoading={isLoading}
              getAggregated={getAggregated}
              accountId={accountId}
              onAccountChange={setAccountId}
            />
          )}

          {activeTab === "strategy" && (
            <StrategyAnalysisTab trades={trades} isLoading={isLoading} />
          )}

          {activeTab === "risk" && (
            <RiskMetricsTab trades={trades} isLoading={isLoading} />
          )}

          {activeTab === "behavior" && (
            <BehaviorAnalysisTab trades={trades} isLoading={isLoading} />
          )}
        </div>
      )}
    </div>
  );
}
