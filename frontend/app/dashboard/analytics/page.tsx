"use client";

/**
 * Analytics Hub — /dashboard/analytics
 *
 * Active section is driven by the `?tab=` URL search param, which is set by
 * the sidebar AnalyticsNavItem. No in-page secondary navigation exists — all
 * tab switching happens through the main sidebar.
 */

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { BarChart2 } from "lucide-react";

import { useReportData } from "@/hooks/useReportData";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { Spinner } from "@/components/ui/Spinner";
import { TimeAnalysisTab } from "./TimeAnalysisTab";
import { StrategyAnalysisTab } from "./StrategyAnalysisTab";
import { RiskMetricsTab } from "./RiskMetricsTab";
import { BehaviorAnalysisTab } from "./BehaviorAnalysisTab";

// ─── Types ────────────────────────────────────────────────────────────────────

type TabId = "time" | "strategy" | "risk" | "behavior";

// ─── Component ────────────────────────────────────────────────────────────────

export default function AnalyticsHubPage() {
  const searchParams = useSearchParams();

  // Resolve active tab from URL, default to "time"
  const rawTab = searchParams.get("tab");
  const activeTab: TabId =
    rawTab === "strategy" || rawTab === "risk" || rawTab === "behavior"
      ? rawTab
      : "time";

  // Single global account filter
  const [accountId, setAccountId] = useState<string | null>(null);

  // Fetch all report data once at page level
  const { trades, getAggregated, isLoading, isError } =
    useReportData(accountId);

  return (
    <div className="flex flex-col gap-4">
      {/* ── Page header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-foreground leading-tight">
            Analytics Hub
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-lg">
            Deep-dive into your trading performance across time, strategy, risk, and behavior.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-4">
          <AccountFilter value={accountId} onChange={setAccountId} />
        </div>
      </div>

      {/* ── Error banner ─────────────────────────────────────────────────────── */}
      {isError && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-600 dark:text-rose-400 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 shrink-0" />
          <span>Failed to load trade data. Please refresh or try again later.</span>
        </div>
      )}

      {/* ── Tab content ──────────────────────────────────────────────────────── */}
      {isLoading && trades.length === 0 ? (
        <div className="flex items-center justify-center py-32">
          <Spinner size="lg" />
        </div>
      ) : (
        <div>
          {activeTab === "time" && (
            <TimeAnalysisTab
              trades={trades}
              isLoading={isLoading}
              getAggregated={getAggregated}
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

