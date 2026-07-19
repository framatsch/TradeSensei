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

/**
 * ImportDateRange — broker-agnostic date-range control for sync imports.
 *
 * Driven by a BrokerImportCapability descriptor that supplies maxWindowDays
 * (clamp + limit badge) and syncParam (how the chosen range serializes into
 * the sync request — consumed by the parent, not this component).
 *
 * Always renders the fill bar + YTD/custom toggle for every broker type.
 * The syncParam descriptor only affects how the parent serializes the chosen
 * range into the sync request (from_date for IBKR, days for Schwab).
 */

"use client";

import { useMemo } from "react";
import type { FlexFromDatePreset } from "@/lib/types";
import type { BrokerImportCapability } from "@/components/imports/ImportCapability";

interface ImportDateRangeProps {
  capability: BrokerImportCapability;
  preset: FlexFromDatePreset;
  customFromDate: string;
  onPresetChange: (preset: FlexFromDatePreset) => void;
  onCustomFromDateChange: (date: string) => void;
  disabled?: boolean;
}

function parseYYYYMMDD(s: string): Date | null {
  if (!s || s.length !== 8) return null;
  const y = parseInt(s.slice(0, 4), 10);
  const m = parseInt(s.slice(4, 6), 10) - 1;
  const d = parseInt(s.slice(6, 8), 10);
  const dt = new Date(y, m, d);
  return isNaN(dt.getTime()) ? null : dt;
}

function formatDisplay(d: Date): string {
  if (typeof navigator !== "undefined" && navigator.language) {
    return d.toLocaleDateString(navigator.language, { day: "2-digit", month: "short", year: "numeric" });
  }
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

function toYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function toInputDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fromInputDate(s: string): string {
  return s.replace(/-/g, "");
}

export function ImportDateRange({
  capability,
  preset,
  customFromDate,
  onPresetChange,
  onCustomFromDateChange,
  disabled = false,
}: ImportDateRangeProps) {
  const { maxWindowDays } = capability;
  const today = useMemo(() => new Date(), []);

  const startDate = useMemo(() => {
    if (preset === "ytd") {
      return new Date(today.getFullYear(), 0, 1);
    }
    const parsed = parseYYYYMMDD(customFromDate);
    if (!parsed) return new Date(today.getFullYear(), 0, 1);
    return parsed;
  }, [preset, customFromDate, today]);

  const earliestAllowed = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - maxWindowDays);
    return d;
  }, [today, maxWindowDays]);

  const effectiveStart = startDate < earliestAllowed ? earliestAllowed : startDate;

  const msInDay = 86_400_000;
  const daysCovered = Math.max(
    1,
    Math.ceil((today.getTime() - effectiveStart.getTime()) / msInDay)
  );
  const fillPct = Math.min(100, Math.round((daysCovered / maxWindowDays) * 100));

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
        <div className="flex rounded-md overflow-hidden border border-border text-xs">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onPresetChange("ytd")}
            className={[
              "px-3 py-1.5 font-medium transition-colors",
              preset === "ytd"
                ? "bg-primary text-white"
                : "bg-secondary text-muted-foreground hover:bg-muted",
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
                onCustomFromDateChange(toYYYYMMDD(earliestAllowed));
              }
            }}
            className={[
              "px-3 py-1.5 font-medium transition-colors border-l border-border",
              preset === "custom"
                ? "bg-primary text-white"
                : "bg-secondary text-muted-foreground hover:bg-muted",
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
            className="px-2 py-1 text-xs bg-secondary border border-border rounded text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
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
          <div className="absolute right-0 top-0 h-full w-0.5 bg-muted-foreground" />
        </div>

        {/* Labels */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatDisplay(effectiveStart)}</span>
          <span className="text-muted-foreground text-center">
            {daysCovered} day{daysCovered !== 1 ? "s" : ""}
          </span>
          <span>Today ({formatDisplay(today)})</span>
        </div>
      </div>

      {/* Limit badge */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1 bg-[color-mix(in_srgb,var(--warning)_20%,transparent)] text-warning px-2 py-0.5 rounded-full font-medium">
          <span>⚠</span>
          Max. {maxWindowDays} days
        </span>
        {fillPct >= 95 && (
          <span className="text-warning">
            — You are near the {maxWindowDays}-day limit.
          </span>
        )}
      </div>
    </div>
  );
}
