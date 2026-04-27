"use client";

import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";

export function ChartDisplaySettings() {
  const { data: settings, isLoading } = useSettings();
  const { mutateAsync: updateSettings } = useUpdateSettings();
  const queryClient = useQueryClient();

  const [candlesBefore, setCandlesBefore] = useState<string>("20");
  const [candlesAfter, setCandlesAfter] = useState<string>("10");
  const [showPostExit, setShowPostExit] = useState<boolean>(false);
  const [homeRoute, setHomeRoute] = useState<"/dashboard" | "/dashboard/trades" | "/dashboard/library">("/dashboard");

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setCandlesBefore(String(settings.chart_candles_before ?? 20));
      setCandlesAfter(String(settings.chart_candles_after ?? 10));
      setShowPostExit(settings.chart_show_post_exit ?? false);
      setHomeRoute(settings.home_route ?? "/dashboard");
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
        chart_candles_before: before,
        chart_candles_after: after,
        chart_show_post_exit: showPostExit,
        home_route: homeRoute,
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
      }
    } finally {
      setIsSaving(false);
    }
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
        <h3 className="text-lg font-medium text-foreground">Look & Feel</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Customize your chart display defaults and home page.
        </p>
      </div>

      <div className="space-y-6">
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
            <option value="/dashboard">Portfolio Overview</option>
            <option value="/dashboard/trades">Journal</option>
            <option value="/dashboard/library">Strategy & Tags</option>
          </select>
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