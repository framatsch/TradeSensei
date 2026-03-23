"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { useReportData } from "@/hooks/useReportData";

// ISO day_of_week mapping: 0 = Monday, …, 6 = Sunday (matching the backend filter convention).
const DAY_MAP: Record<string, number> = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6,
};

export default function WeekdayPage() {
  const [accountId, setAccountId] = useState<string | null>(null);
  const { getAggregated, isLoading } = useReportData(accountId);
  const router = useRouter();

  // name is like "Monday", "Tuesday" — map to ISO day-of-week integer.
  const handleNavigate = useCallback(
    (row: PerformanceDataPoint) => {
      const dow = DAY_MAP[row.name];
      if (dow === undefined) return;
      const params = new URLSearchParams({ day_of_week: String(dow) });
      if (accountId) params.set("account_id", accountId);
      router.push(`/dashboard/trades?${params.toString()}`);
    },
    [router, accountId]
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
        <PageHeader title="Weekday" subtitle="Performance breakdown by day of week" />
        <AccountFilter value={accountId} onChange={setAccountId} />
      </div>
      <PerformanceAnalysisDashboard
        data={getAggregated("Weekday")}
        dimensionLabel="Weekday"
        onViewReport={handleNavigate}
        onBarClick={handleNavigate}
      />
    </div>
  );
}
