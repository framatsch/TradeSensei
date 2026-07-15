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
 * FeaturesSettings — per-user feature flag toggles with a deferred Apply button.
 *
 * Changes are held in local draft state and only written to the backend when
 * "Apply Changes" is clicked. The Apply button is disabled when there are no
 * pending changes and goes back to disabled after a successful save.
 */

"use client";

import React, { useState } from "react";
import { FEATURE_FLAGS } from "@/lib/featureFlags";
import { useUpdateSettings, useSettings } from "@/hooks/useSettings";

export default function FeaturesSettings() {
  const { data: settings } = useSettings();
  const update = useUpdateSettings();

  // Local draft: only keys that differ from the current server state
  const [draft, setDraft] = useState<Record<string, boolean>>({});
  const [showOpenTradesDraft, setShowOpenTradesDraft] = useState<boolean | null>(null);

  const serverFeatures = (settings?.features ?? {}) as Record<string, boolean>;
  const showOpenTradesEnabled = settings?.show_open_trades ?? false;
  const effectiveShowOpenTrades = showOpenTradesDraft ?? showOpenTradesEnabled;
  // Effective values: server state with draft overrides applied on top
  const effective = { ...serverFeatures, ...draft };

  const hasPending = Object.keys(draft).length > 0 || showOpenTradesDraft !== null;

  const handleToggle = (key: string, currentValue: boolean) => {
    const newValue = !currentValue;
    setDraft((prev) => {
      const serverVal = serverFeatures[key] ?? false;
      // If toggling back to the server value, remove key from draft
      if (newValue === serverVal) {
        const { [key]: _removed, ...rest } = prev;
        return rest;
      }
      return { ...prev, [key]: newValue };
    });
  };

  const handleApply = () => {
    if (!hasPending) return;
    const allFeatures = { ...serverFeatures, ...draft };
    const payload: { features: Record<string, boolean>; show_open_trades?: boolean } = {
      features: allFeatures,
    };
    if (showOpenTradesDraft !== null) {
      payload.show_open_trades = showOpenTradesDraft;
    }
    update.mutate(
      payload,
      {
        onSuccess: () => {
          setDraft({});
          setShowOpenTradesDraft(null);
        },
      }
    );
  };

  const handleShowOpenTradesToggle = () => {
    const nextValue = !effectiveShowOpenTrades;
    setShowOpenTradesDraft(nextValue === showOpenTradesEnabled ? null : nextValue);
  };

  return (
    <div className="space-y-4 max-w-lg">
      {/* Section header */}
      <div>
        <h3 className="text-sm font-semibold text-foreground">Features</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Enable or disable optional modules. Changes are staged locally and saved with Apply.
        </p>
      </div>

      {/* Flag list */}
      <div className="space-y-2">
        <div
          className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border bg-card"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">Show Open Trades</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Show open positions in trade lists and enable the Open/Closed filter.
            </p>
          </div>

          <button
            role="switch"
            aria-checked={effectiveShowOpenTrades}
            aria-label="Show Open Trades"
            onClick={handleShowOpenTradesToggle}
            type="button"
            className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
              effectiveShowOpenTrades ? "bg-primary" : "bg-muted"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-150 ${
                effectiveShowOpenTrades ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {FEATURE_FLAGS.map((f) => {
          const enabled = effective[f.key] ?? false;
          return (
            <div
              key={f.key}
              className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border bg-card"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">{f.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{f.description}</p>
              </div>

              {/* Toggle switch — uses role="switch" for ARIA + test selectors */}
              <button
                role="switch"
                aria-checked={enabled}
                aria-label={f.label}
                onClick={() => !f.comingSoon && handleToggle(f.key, enabled)}
                disabled={f.comingSoon}
                type="button"
                className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-40 disabled:cursor-not-allowed ${
                  enabled ? "bg-primary" : "bg-muted"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-150 ${
                    enabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          );
        })}
      </div>

      {/* Apply button */}
      <div className="flex justify-end pt-1">
        <button
          type="button"
          onClick={handleApply}
          disabled={!hasPending || update.isPending}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {update.isPending ? "Applying…" : "Apply Changes"}
        </button>
      </div>
    </div>
  );
}
