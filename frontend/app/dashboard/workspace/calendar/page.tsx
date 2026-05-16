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

import { useRouter } from "next/navigation";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useReportData } from "@/hooks/useReportData";
import { Calendar } from "@/components/calendar/Calendar";
import { Spinner } from "@/components/ui/Spinner";

export default function CalendarPage() {
  const router = useRouter();
  const { filter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();
  const { calendarData, isLoading, isError } = useReportData(portfolioId, filter);

  const handleDayClick = (dateStr: string) => {
    // Calendar component ensures only days with trades are clickable
    router.push(`/dashboard/trades?date_from=${dateStr}&date_to=${dateStr}`);
  };

  return (
    <div className="p-6 space-y-6">
      {isError && (
          <div className="bg-destructive/10 text-destructive px-4 py-3 rounded-md text-sm">
            Failed to load calendar data.
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Spinner size="lg" />
          </div>
        ) : (
          <Calendar data={calendarData} onDayClick={handleDayClick} />
        )}
    </div>
  );
}

