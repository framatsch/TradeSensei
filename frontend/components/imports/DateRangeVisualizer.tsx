/**
 * DateRangeVisualizer — shows the IBKR Flex import date range visually.
 *
 * Renders a timeline bar from the selected start date to today, with a
 * visual fill representing how much of the allowed 1-year window is used.
 * The user can switch between "YTD" (January 1 of the current year) and
 * a custom start date, subject to the IBKR 1-year maximum limit.
 */

"use client";

import { useMemo } from "react";
import type { FlexFromDatePreset } from "@/lib/types";

interface DateRangeVisualizerProps {
  /** Currently selected preset mode. */
  preset: FlexFromDatePreset;
  /** Custom start date in YYYYMMDD format. Only used when preset = "custom". */
  customFromDate: string;
  /** Callback when the preset changes. */
  onPresetChange: (preset: FlexFromDatePreset) => void;
  /** Callback when the custom start date changes. */
  onCustomFromDateChange: (date: string) => void;
  /** Whether controls are disabled (e.g. while syncing). */
  disabled?: boolean;
}

const MAX_DAYS = 365;

function parseYYYYMMDD(s: string): Date | null {
  if (!s || s.length !== 8) return null;
  const y = parseInt(s.slice(0, 4), 10);
  const m = parseInt(s.slice(4, 6), 10) - 1;
  const d = parseInt(s.slice(6, 8), 10);
  const dt = new Date(y, m, d);
  return isNaN(dt.getTime()) ? null : dt;
}

function formatDisplay(d: Date): string {
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" });
}

function toYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function toInputDate(d: Date): string {
  // Returns yyyy-mm-dd for <input type="date">
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fromInputDate(s: string): string {
  // Converts yyyy-mm-dd to YYYYMMDD
  return s.replace(/-/g, "");
}

export function DateRangeVisualizer({
  preset,
  customFromDate,
  onPresetChange,
  onCustomFromDateChange,
  disabled = false,
}: DateRangeVisualizerProps) {
  const today = useMemo(() => new Date(), []);

  // Compute the effective start date
  const startDate = useMemo(() => {
    if (preset === "ytd") {
      return new Date(today.getFullYear(), 0, 1); // Jan 1 of current year
    }
    const parsed = parseYYYYMMDD(customFromDate);
    if (!parsed) return new Date(today.getFullYear(), 0, 1);
    return parsed;
  }, [preset, customFromDate, today]);

  // Clamp start date: cannot be more than MAX_DAYS ago
  const earliestAllowed = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - MAX_DAYS);
    return d;
  }, [today]);

  const effectiveStart = startDate < earliestAllowed ? earliestAllowed : startDate;

  // Days covered and percentage fill
  const msInDay = 86_400_000;
  const daysCovered = Math.max(
    1,
    Math.ceil((today.getTime() - effectiveStart.getTime()) / msInDay)
  );
  const fillPct = Math.min(100, Math.round((daysCovered / MAX_DAYS) * 100));

  // Min/max for the date input
  const minInputDate = toInputDate(earliestAllowed);
  const maxInputDate = toInputDate(today);

  const inputValue = useMemo(() => {
    if (preset !== "custom") return "";
    const parsed = parseYYYYMMDD(customFromDate);
    return parsed ? toInputDate(parsed) : "";
  }, [preset, customFromDate]);

  return (
    <div className="space-y-3">
      {/* Preset toggle */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground shrink-0">
          From:
        </span>
        <div className="flex rounded-md overflow-hidden border border-border dark:border-border text-xs">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPresetChange("ytd")}
            className={[
              "px-3 py-1.5 font-medium transition-colors",
              preset === "ytd"
                ? "bg-primary text-white"
                : "bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600",
              disabled ? "opacity-50 cursor-not-allowed" : "",
            ].join(" ")}
          >
            YTD (Jan 1, {today.getFullYear()})
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => {
              onPresetChange("custom");
              if (!customFromDate) {
                // Default to earliest allowed date
                onCustomFromDateChange(toYYYYMMDD(earliestAllowed));
              }
            }}
            className={[
              "px-3 py-1.5 font-medium transition-colors border-l border-border dark:border-border",
              preset === "custom"
                ? "bg-primary text-white"
                : "bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600",
              disabled ? "opacity-50 cursor-not-allowed" : "",
            ].join(" ")}
          >
            Custom date
          </button>
        </div>

        {/* Custom date picker */}
        {preset === "custom" && (
          <input
            type="date"
            value={inputValue}
            min={minInputDate}
            max={maxInputDate}
            disabled={disabled}
            onChange={(e) => onCustomFromDateChange(fromInputDate(e.target.value))}
            className="px-2 py-1 text-xs bg-secondary border border-border dark:border-border rounded text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          />
        )}
      </div>

      {/* Visual timeline bar */}
      <div className="space-y-1">
        <div className="relative h-6 bg-secondary rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300"
            style={{ width: `${fillPct}%` }}
          />
          {/* Today marker */}
          <div className="absolute right-0 top-0 h-full w-0.5 bg-slate-400 dark:bg-slate-500" />
        </div>

        {/* Labels */}
        <div className="flex items-center justify-between text-xs text-muted-foreground dark:text-slate-400">
          <span>{formatDisplay(effectiveStart)}</span>
          <span className="text-slate-400 dark:text-muted-foreground text-center">
            {daysCovered} day{daysCovered !== 1 ? "s" : ""}
          </span>
          <span>Today ({formatDisplay(today)})</span>
        </div>
      </div>

      {/* Limit badge */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground dark:text-slate-400">
        <span className="inline-flex items-center gap-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium">
          <span>⚠</span>
          IBKR Flex: max. 1 year
        </span>
        {fillPct >= 95 && (
          <span className="text-amber-500 dark:text-amber-400">
            — You are near the {MAX_DAYS}-day limit.
          </span>
        )}
      </div>
    </div>
  );
}
