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
    if (preset === "mtd") {
      return new Date(today.getFullYear(), today.getMonth(), 1);
    }
    if (preset.endsWith("d")) {
      const days = parseInt(preset.replace("d", ""), 10);
      const d = new Date(today);
      d.setDate(d.getDate() - days);
      return d;
    }
    // preset === "custom"
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

  const minInputDate = toInputDate(earliestAllowed);
  const maxInputDate = toInputDate(today);

  const inputValue = useMemo(() => {
    return toInputDate(effectiveStart);
  }, [effectiveStart]);

  return (
    <div className="space-y-3">
      {/* Date Selection Row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground shrink-0">
          From:
        </span>
        
        <select
          className="px-2 py-1.5 text-xs bg-secondary border border-border rounded text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          disabled={disabled}
          value={preset}
          onChange={(e) => {
            const val = e.target.value as FlexFromDatePreset;
            onPresetChange(val);
            if (val === "custom") {
              onCustomFromDateChange(toYYYYMMDD(effectiveStart));
            }
          }}
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="180d">Last 180 days</option>
          <option value="360d">Last 360 days</option>
          <option value="mtd">Month to date</option>
          <option value="ytd">Year to date</option>
          <option value="custom">Custom date...</option>
        </select>

        <input
          type="date"
          value={inputValue}
          min={minInputDate}
          max={maxInputDate}
          disabled={disabled}
          onChange={(e) => {
            onPresetChange("custom");
            onCustomFromDateChange(fromInputDate(e.target.value));
          }}
          className="px-2 py-1 text-xs bg-secondary border border-border rounded text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
      </div>

      {/* Limit hint */}
      <div className="text-xs text-muted-foreground mt-1">
        Selected: {daysCovered} day{daysCovered !== 1 ? "s" : ""}
        <span className="mx-1.5 opacity-50">•</span>
        Broker API limit: {maxWindowDays} days
      </div>
    </div>
  );
}
