"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { useReportData } from "@/hooks/useReportData";

// Maps 3-letter month abbreviation to 0-based month index.
const MONTH_INDEX: Record<string, number> = {
  Jan: 0, Feb: 1, Mar: 2, Apr: 3,
  May: 4, Jun: 5, Jul: 6, Aug: 7,
  Sep: 8, Oct: 9, Nov: 10, Dec: 11,
};

export default function MonthlyPage() {
  const [accountId, setAccountId] = useState<string | null>(null);
  const { getAggregated, isLoading, trades } = useReportData(accountId);
  const router = useRouter();

  // name is like "Feb", "Mar" — find earliest and latest opened_at dates for trades
  // in that calendar month across all years, then use those as the date range filter.
  const handleNavigate = useCallback(
    (row: PerformanceDataPoint) => {
      const monthIdx = MONTH_INDEX[row.name];
      if (monthIdx === undefined) return;

      const matchingDates = trades
        .filter((t) => {
          if (!t.opened_at) return false;
          return new Date(t.opened_at).getMonth() === monthIdx;
        })
        .map((t) => t.opened_at as string)
        .sort();

      if (matchingDates.length === 0) return;

      const from = matchingDates[0].slice(0, 10) + "T00:00:00Z";
      const to = matchingDates[matchingDates.length - 1].slice(0, 10) + "T23:59:59Z";

      const params = new URLSearchParams({ opened_at_from: from, opened_at_to: to });
      if (accountId) params.set("account_id", accountId);
      router.push(`/dashboard/trades?${params.toString()}`);
    },
    [router, accountId, trades]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <PageHeader title="Month" subtitle="Performance breakdown by calendar month" />
        <AccountFilter value={accountId} onChange={setAccountId} />
      </div>
      <PerformanceAnalysisDashboard
        data={getAggregated("Monthly")}
        dimensionLabel="Monthly"
        onViewReport={handleNavigate}
        onBarClick={handleNavigate}
      />
    </div>
  );
}
