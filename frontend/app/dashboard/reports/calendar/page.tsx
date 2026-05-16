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

"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { Calendar } from "@/components/calendar";
import { useReportData } from "@/hooks/useReportData";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";

export default function CalendarPage() {
  const { activePortfolioId } = useActivePortfolio();
  const { calendarData, isLoading, isError } = useReportData();
  const router = useRouter();

  const handleDayClick = useCallback((date: string) => {
    const params = new URLSearchParams({
      closed_at_from: date,
      closed_at_to: date,
      ...(activePortfolioId ? { portfolio_id: activePortfolioId } : {}),
    });
    router.push(`/dashboard/trades?${params.toString()}`);
  }, [router, activePortfolioId]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <PageHeader title="Calendar" subtitle="Daily P&L and trade activity at a glance" />
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
