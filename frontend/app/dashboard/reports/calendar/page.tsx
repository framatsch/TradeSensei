"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { AccountFilter } from "@/components/ui/AccountFilter";
import { Calendar } from "@/components/calendar";
import { useReportData } from "@/hooks/useReportData";

export default function CalendarPage() {
  const [accountId, setAccountId] = useState<string | null>(null);
  const { calendarData, isLoading, isError } = useReportData(accountId);
  const router = useRouter();

  const handleDayClick = useCallback((date: string) => {
    const params = new URLSearchParams({
      opened_at_from: date,
      opened_at_to: date,
      ...(accountId ? { account_id: accountId } : {}),
    });
    router.push(`/dashboard/trades?${params.toString()}`);
  }, [router, accountId]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <PageHeader title="Calendar" subtitle="Daily P&L and trade activity at a glance" />
        <AccountFilter value={accountId} onChange={setAccountId} />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      ) : isError ? (
        <div className="text-center py-10 text-muted-foreground text-sm">
          No trade data available.
        </div>
      ) : (
        <Calendar
          data={calendarData}
          currencySymbol="$"
          initialViewMode="month"
          onDayClick={handleDayClick}
        />
      )}
    </div>
  );
}
