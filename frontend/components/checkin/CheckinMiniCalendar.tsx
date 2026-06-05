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

import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useMemo } from "react";

export function CheckinMiniCalendar() {
  const { filter, setFilter } = useCheckinFilter();
  const { month } = filter;
  const setMonth = (m: string) => setFilter(prev => ({ ...prev, month: m, page: 1 }));
  const router = useRouter();
  const params = useParams();
  const selectedDate = params?.date as string | undefined;
  const { data: phases } = useGetTaxonomies("checkins");

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
  const { data } = useCheckinEntries(fromDate, toDate, undefined, undefined, undefined, 31);

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
      const isSelected = dateStr === (selectedDate || todayStr);
      const dayOfWeek = (firstDay + i - 1) % 7;
      const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

      let textClass = "text-[color-mix(in_srgb,var(--muted-foreground)_70%,transparent)]";
      if (isSelected) {
        textClass = "text-primary-foreground";
      } else if (isWeekend) {
        textClass = "text-destructive font-medium hover:text-[color-mix(in_srgb,var(--destructive)_80%,transparent)]";
      } else if (hasCheckin) {
        textClass = "text-foreground font-medium";
      }

      let bgClass = "hover:bg-muted";
      if (isSelected) {
        bgClass = "bg-primary hover:opacity-90 font-semibold";
      } else if (isToday) {
        bgClass = "bg-secondary hover:bg-muted ring-1 ring-primary";
      }

      days.push(
        <button
          key={dateStr}
          onClick={() => {
            router.push(`/dashboard/checkins/${dateStr}`);
          }}
          className={`relative h-8 w-8 flex items-center justify-center rounded-full text-sm transition-colors cursor-pointer ${bgClass} ${textClass}`}
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
      <div className="flex flex-col gap-2 mb-4">
        {/* Month/Year Selection Row (Centered) */}
        <div className="flex items-center justify-center gap-1 font-semibold text-sm w-full">
          <select
            value={m}
            onChange={(e) => {
              const newM = parseInt(e.target.value, 10);
              const newDate = new Date(Date.UTC(year, newM, 1));
              setMonth(newDate.toISOString().slice(0, 7));
            }}
            className="bg-transparent cursor-pointer outline-none appearance-none hover:bg-muted py-1 pl-2 pr-1 rounded-md transition-colors text-foreground focus:ring-1 focus:ring-primary"
            aria-label="Select month"
          >
            {monthNames.map((name, i) => (
              <option key={name} value={i} className="bg-background text-foreground">{name}</option>
            ))}
          </select>
          <select
            value={year}
            onChange={(e) => {
              const newY = parseInt(e.target.value, 10);
              const newDate = new Date(Date.UTC(newY, m, 1));
              setMonth(newDate.toISOString().slice(0, 7));
            }}
            className="bg-transparent cursor-pointer outline-none appearance-none hover:bg-muted py-1 pl-2 pr-1 rounded-md transition-colors text-foreground focus:ring-1 focus:ring-primary"
            aria-label="Select year"
          >
            {Array.from({ length: 11 }, (_, i) => year - 5 + i).map(y => (
              <option key={y} value={y} className="bg-background text-foreground">{y}</option>
            ))}
          </select>
        </div>
        
        {/* Navigation Arrows Row */}
        <div className="flex items-center justify-between w-full px-2">
          <button
            onClick={handlePrevMonth}
            className="p-1 hover:bg-muted rounded-md transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-5 h-5 text-muted-foreground" />
          </button>
          
          <button
            onClick={handleNextMonth}
            className="p-1 hover:bg-muted rounded-md transition-colors"
            aria-label="Next month"
          >
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Days of week */}
    <div className="grid grid-cols-7 gap-1 mb-2 text-center">
      {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
        <div key={day} className={`text-[10px] font-medium uppercase ${day === "Sa" || day === "Su" ? "text-[color-mix(in_srgb,var(--destructive)_80%,transparent)]" : "text-muted-foreground"}`}>
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
