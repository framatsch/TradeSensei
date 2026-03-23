"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { useReportData } from "@/hooks/useReportData";

export default function HourlyPage() {
  const [accountId, setAccountId] = useState<string | null>(null);
  const { getAggregated, isLoading } = useReportData(accountId);
  const router = useRouter();

  // name is like "14:00", "09:00" — extract the hour as an integer.
  const handleNavigate = useCallback(
    (row: PerformanceDataPoint) => {
      const hour = parseInt(row.name.split(":")[0], 10);
      if (isNaN(hour)) return;
      const params = new URLSearchParams({ hour_of_day: String(hour) });
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
        <PageHeader title="Hourly" subtitle="Performance breakdown by hour of day" />
        <AccountFilter value={accountId} onChange={setAccountId} />
      </div>
      <PerformanceAnalysisDashboard
        data={getAggregated("Hourly")}
        dimensionLabel="Hourly"
        onViewReport={handleNavigate}
        onBarClick={handleNavigate}
      />
    </div>
  );
}
