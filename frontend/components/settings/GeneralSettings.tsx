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

import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import { useTheme } from "next-themes";
import type { Theme } from "@/lib/types";

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

export function GeneralSettings() {
  const { data: settings, isLoading } = useSettings();
  const { mutateAsync: updateSettings } = useUpdateSettings();
  const queryClient = useQueryClient();

  const [candlesBefore, setCandlesBefore] = useState<string>("20");
  const [candlesAfter, setCandlesAfter] = useState<string>("10");
  const [showPostExit, setShowPostExit] = useState<boolean>(false);
  const [homeRoute, setHomeRoute] = useState<"/dashboard" | "/dashboard/trades" | "/dashboard/library" | "/dashboard/checkins">("/dashboard");
  const [defaultMarkdownMode, setDefaultMarkdownMode] = useState<"write" | "preview">("write");

  const { theme, setTheme } = useTheme();

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      // @ts-ignore
      setCandlesBefore(String(settings.chart_candles_before ?? 20));
      // @ts-ignore
      setCandlesAfter(String(settings.chart_candles_after ?? 10));
      // @ts-ignore
      setShowPostExit(settings.chart_show_post_exit ?? false);
      // @ts-ignore
      setHomeRoute(settings.home_route ?? "/dashboard");
      // @ts-ignore
      setDefaultMarkdownMode(settings.default_markdown_mode ?? "write");
    }
  }, [settings]);

  const handleSave = async () => {
    setError(null);
    const before = parseInt(candlesBefore, 10);
    const after = parseInt(candlesAfter, 10);

    if (isNaN(before) || before <= 0) {
      setError("Candles before entry must be a positive whole number");
      return;
    }
    if (isNaN(after) || after <= 0) {
      setError("Candles after exit must be a positive whole number");
      return;
    }

    setIsSaving(true);
    try {
      await updateSettings({
        // @ts-ignore
        chart_candles_before: before,
        // @ts-ignore
        chart_candles_after: after,
        // @ts-ignore
        chart_show_post_exit: showPostExit,
        // @ts-ignore
        home_route: homeRoute,
        // @ts-ignore
        default_markdown_mode: defaultMarkdownMode,
        theme: theme as Theme,
      });
      toast.success("Settings saved successfully");
      queryClient.invalidateQueries({ queryKey: ["users", "me", "settings"] });
    } catch (err) {
      toast.error("Failed to save settings");
      // Revert form state
      if (settings) {
        setCandlesBefore(String(settings.chart_candles_before ?? 20));
        setCandlesAfter(String(settings.chart_candles_after ?? 10));
        setShowPostExit(settings.chart_show_post_exit ?? false);
        setHomeRoute(settings.home_route ?? "/dashboard");
        setTheme(settings.theme ?? "system");
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleThemeChange = (value: Theme) => {
    setTheme(value);
    updateSettings({ theme: value });
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-lg opacity-50 pointer-events-none animate-pulse">
        <div className="h-20 bg-muted rounded-lg" />
        <div className="h-20 bg-muted rounded-lg" />
        <div className="h-20 bg-muted rounded-lg" />
        <div className="h-20 bg-muted rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-lg">
      <div>
        <h3 className="text-lg font-medium text-foreground">General</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Customize your interface theme, chart display defaults and home page.
        </p>
      </div>

      <div className="space-y-6">
        {/* ── Theme ─────────────────────────────────────────────────────── */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Theme
          </label>
          <div className="flex gap-2 mt-1">
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleThemeChange(opt.value)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 ${
                  theme === opt.value
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

        <hr className="border-border" />

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Candles before entry
          </label>
          <input
            type="number"
            min="1"
            step="1"
            value={candlesBefore}
            onChange={(e) => setCandlesBefore(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Candles after exit
          </label>
          <input
            type="number"
            min="1"
            step="1"
            value={candlesAfter}
            onChange={(e) => setCandlesAfter(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={showPostExit}
            onClick={() => setShowPostExit(!showPostExit)}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
              showPostExit ? "bg-primary" : "bg-muted"
            }`}
          >
            <span
              aria-hidden="true"
              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                showPostExit ? "translate-x-4" : "translate-x-0"
              }`}
            />
          </button>
          <label className="text-sm font-medium text-foreground cursor-pointer" onClick={() => setShowPostExit(!showPostExit)}>
            Show post-exit candles by default
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Default Home Page
          </label>
          <select
            value={homeRoute}
            onChange={(e) => setHomeRoute(e.target.value as any)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="/dashboard">Portfolio Workspace</option>
            <option value="/dashboard/trades">Trading Log</option>
            <option value="/dashboard/library">Global Library</option>
            <option value="/dashboard/checkins">Market Check-in</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Default Markdown Mode
          </label>
          <select
            value={defaultMarkdownMode}
            onChange={(e) => setDefaultMarkdownMode(e.target.value as "write" | "preview")}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="write">Edit Mode</option>
            <option value="preview">Preview Mode</option>
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            Choose whether markdown editors should open in edit or preview mode initially.
          </p>
        </div>

        {error && (
          <p className="text-sm text-danger mt-2">{error}</p>
        )}

        <div className="pt-4">
          <button
            onClick={handleSave}
            disabled={isSaving || (error !== null && error !== "")}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50 transition-opacity"
          >
            {isSaving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}