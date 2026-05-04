"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useMarketPhases } from "@/hooks/useCheckinDefinitions";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

export function CheckinMiniCalendar() {
  const { month, setMonth } = useCheckinParams();
  const router = useRouter();
  const { data: phases } = useMarketPhases();

  // Parse current month
  const currentDate = new Date(`${month}-01T00:00:00Z`);
  const year = currentDate.getUTCFullYear();
  const m = currentDate.getUTCMonth(); // 0-11

  const handlePrevMonth = () => {
    const prev = new Date(Date.UTC(year, m - 1, 1));
    setMonth(prev.toISOString().slice(0, 7));
  };

  const handleNextMonth = () => {
    const next = new Date(Date.UTC(year, m + 1, 1));
    setMonth(next.toISOString().slice(0, 7));
  };

  // Calculate days in month
  const daysInMonth = new Date(Date.UTC(year, m + 1, 0)).getUTCDate();
  
  // Calculate first day of month (0 = Sunday, 1 = Monday...)
  const firstDay = new Date(Date.UTC(year, m, 1)).getUTCDay();

  // Fetch checkins for this month
  const fromDate = `${month}-01`;
  const toDate = `${month}-${daysInMonth.toString().padStart(2, "0")}`;
  const { data } = useCheckinEntries(fromDate, toDate, undefined, 31);

  // Map dates to regime colors
  const dateColors = useMemo(() => {
    const map = new Map<string, string>();
    if (data?.items) {
      for (const checkin of data.items) {
        if (checkin.market_phase) {
          const phase = phases?.find(p => p.name === checkin.market_phase);
          map.set(checkin.date, phase?.color_hex ?? "#94a3b8");
        } else {
           map.set(checkin.date, "#94a3b8"); // fallback color
        }
      }
    }
    return map;
  }, [data, phases]);

  const todayStr = new Date().toISOString().slice(0, 10);

  const renderDays = () => {
    const days = [];
    // Empty slots for start of month
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`empty-${i}`} className="h-8" />);
    }

    // Actual days
    for (let i = 1; i <= daysInMonth; i++) {
      const dateStr = `${month}-${i.toString().padStart(2, "0")}`;
      const color = dateColors.get(dateStr);
      const hasCheckin = !!color;
      const isToday = dateStr === todayStr;

      days.push(
        <button
          key={dateStr}
          onClick={() => {
            router.push(`/dashboard/checkins/${dateStr}`);
          }}
          className={`relative h-8 w-8 flex items-center justify-center rounded-full text-sm transition-colors cursor-pointer hover:bg-muted ${
            hasCheckin
              ? "text-foreground font-medium"
              : "text-muted-foreground/70"
          } ${isToday && !hasCheckin ? "bg-secondary text-foreground" : ""} ${isToday && hasCheckin ? "ring-1 ring-primary" : ""}`}
        >
          {i}
          {hasCheckin && (
            <div
              className="absolute bottom-1 w-1 h-1 rounded-full"
              style={{ backgroundColor: color }}
            />
          )}
        </button>
      );
    }
    return days;
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm">
          {monthNames[m]} {year}
        </h3>
        <div className="flex space-x-1">
          <button
            onClick={handlePrevMonth}
            className="p-1 hover:bg-muted rounded-md transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleNextMonth}
            className="p-1 hover:bg-muted rounded-md transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Days of week */}
      <div className="grid grid-cols-7 gap-1 mb-2 text-center">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
          <div key={day} className="text-[10px] font-medium uppercase text-muted-foreground">
            {day}
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-1 place-items-center">
        {renderDays()}
      </div>
    </div>
  );
}
