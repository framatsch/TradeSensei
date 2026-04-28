/**
 * GeneralSettings — UI preferences: theme and default date range.
 */

"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import type { DefaultDateRange, Theme } from "@/lib/types";

// ─── Theme selector ────────────────────────────────────────────────────────

const THEME_OPTIONS: { value: Theme; label: string; icon: React.ReactNode }[] = [
  {
    value: "system",
    label: "System",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <path d="M8 21h8M12 17v4" />
      </svg>
    ),
  },
  {
    value: "light",
    label: "Light",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
    ),
  },
  {
    value: "dark",
    label: "Dark",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    ),
  },
];

// ─── Date range options ────────────────────────────────────────────────────

const DATE_RANGE_OPTIONS: { value: DefaultDateRange; label: string; description: string }[] = [
  { value: "all", label: "All Time", description: "Show all trades regardless of date" },
  { value: "ytd", label: "Year to Date", description: "Show trades from January 1 of this year" },
  { value: "last30", label: "Last 30 Days", description: "Show trades from the past 30 days" },
];

// ─── Component ─────────────────────────────────────────────────────────────

export function GeneralSettings() {
  const { setTheme } = useTheme();
  const { data: settings } = useSettings();
  const { mutate: updateSettings } = useUpdateSettings();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleThemeChange = (value: Theme) => {
    setTheme(value);
    updateSettings({ theme: value });
  };

  const handleDateRangeChange = (value: DefaultDateRange) => {
    updateSettings({ default_date_range: value });
  };

  if (!mounted) return null;

  const currentTheme = settings?.theme ?? "system";
  const currentDateRange = settings?.default_date_range ?? "all";

  return (
    <div className="space-y-8 max-w-lg">
      {/* ── Theme ─────────────────────────────────────────────────────── */}
      <div>
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-foreground">Theme</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Choose how Trade Sensei looks. "System" follows your OS preference.
          </p>
        </div>

        <div className="flex gap-2">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleThemeChange(opt.value)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 ${
                currentTheme === opt.value
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card text-muted-foreground border-border hover:bg-muted"
              }`}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Default Date Range ────────────────────────────────────────── */}
      <div>
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-foreground">Default Date Range</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            The date range applied when you open the Trades page or Dashboard without URL filters.
          </p>
        </div>

        <div className="space-y-2">
          {DATE_RANGE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                currentDateRange === opt.value
                  ? "bg-primary/10 border-primary"
                  : "bg-card border-border hover:bg-muted"
              }`}
            >
              <input
                type="radio"
                name="default_date_range"
                value={opt.value}
                checked={currentDateRange === opt.value}
                onChange={() => handleDateRangeChange(opt.value)}
                className="mt-0.5 accent-primary"
              />
              <div>
                <p className={`text-sm font-medium ${
                  currentDateRange === opt.value
                    ? "text-primary"
                    : "text-foreground"
                }`}>
                  {opt.label}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {opt.description}
                </p>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
