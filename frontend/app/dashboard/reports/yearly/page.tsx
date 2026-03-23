"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { PerformanceAnalysisDashboard } from "@/components/trades/PerformanceAnalysisDashboard";
import type { PerformanceDataPoint } from "@/components/trades/PerformanceAnalysisDashboard";
import { useReportData } from "@/hooks/useReportData";

export default function YearlyPage() {
  const [accountId, setAccountId] = useState<string | null>(null);
  const { getAggregated, isLoading } = useReportData(accountId);
  const router = useRouter();

  // name is like "2025", "2026" — build a full-year date range.
  const handleNavigate = useCallback(
    (row: PerformanceDataPoint) => {
      const year = parseInt(row.name, 10);
      if (isNaN(year)) return;
      const params = new URLSearchParams({
        opened_at_from: `${year}-01-01T00:00:00Z`,
        opened_at_to: `${year}-12-31T23:59:59Z`,
      });
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
        <PageHeader title="Year" subtitle="Performance breakdown by year" />
        <AccountFilter value={accountId} onChange={setAccountId} />
      </div>
      <PerformanceAnalysisDashboard
        data={getAggregated("Yearly")}
        dimensionLabel="Yearly"
        onViewReport={handleNavigate}
        onBarClick={handleNavigate}
      />
    </div>
  );
}
