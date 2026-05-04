"use client";

import { useRouter } from "next/navigation";
import { useWorkspaceFilter } from "@/components/workspace/WorkspaceFilterContext";
import { useReportData } from "@/hooks/useReportData";
import { Calendar } from "@/components/calendar/Calendar";
import { Spinner } from "@/components/ui/Spinner";

export default function CalendarPage() {
  const router = useRouter();
  const { filter } = useWorkspaceFilter();
  const { calendarData, isLoading, isError } = useReportData(filter.portfolioId);

  const handleDayClick = (dateStr: string, dayData?: any) => {
    // Only navigate to trades log if there are actually trades on this day
    if (dayData && dayData.trade_count > 0) {
      router.push(`/dashboard/trades?date_from=${dateStr}&date_to=${dateStr}`);
    }
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
