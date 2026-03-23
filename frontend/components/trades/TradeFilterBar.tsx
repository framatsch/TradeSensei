/**
 * TradeFilterBar — collapsible filter panel for the trades list.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useTags } from "@/hooks/useTags";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useAccounts } from "@/hooks/useAccounts";
import { TagBadge } from "@/components/tags/TagBadge";
import type { TradeFilters } from "@/hooks/useTrades";

export type { TradeFilters };

interface Props {
  filters: TradeFilters;
  onChange: (filters: TradeFilters) => void;
}

const ASSET_CLASSES = ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"] as const;

/** Count how many filter fields are non-empty. */
function countActiveFilters(filters: TradeFilters): number {
  let count = 0;
  if (filters.symbol) count++;
  if (filters.direction) count++;
  if (filters.asset_classes?.length) count++;
  if (filters.opened_at_from) count++;
  if (filters.opened_at_to) count++;
  if (filters.tag_ids?.length) count++;
  if (filters.playbook_id) count++;
  if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) count++;
  if (filters.status) count++;
  if (filters.account_id) count++;
  if (filters.hour_of_day !== undefined && filters.hour_of_day !== null) count++;
  if (filters.day_of_week !== undefined && filters.day_of_week !== null) count++;
  return count;
}

const EMPTY_FILTERS: TradeFilters = {
  symbol: "",
  direction: "",
  asset_classes: [],
  opened_at_from: "",
  opened_at_to: "",
  tag_ids: [],
  playbook_id: "",
  pnl_positive: null,
  status: null,
  account_id: "",
  hour_of_day: undefined,
  day_of_week: undefined,
};

const WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatHour(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

const INPUT_CLASS =
  "w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
const LABEL_CLASS = "block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1";

export function TradeFilterBar({ filters, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const activeCount = countActiveFilters(filters);

  // Debounced symbol input
  const [symbolInput, setSymbolInput] = useState(filters.symbol ?? "");
  const symbolTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: tags } = useTags();
  const { data: playbooks } = usePlaybooks();
  const { data: accounts } = useAccounts();

  // Sync external filter changes back into local symbol input
  useEffect(() => {
    setSymbolInput(filters.symbol ?? "");
  }, [filters.symbol]);

  const handleSymbolChange = (value: string) => {
    setSymbolInput(value);
    if (symbolTimerRef.current) clearTimeout(symbolTimerRef.current);
    symbolTimerRef.current = setTimeout(() => {
      onChange({ ...filters, symbol: value || undefined });
    }, 400);
  };

  const handleDirectionChange = (value: string) => {
    onChange({ ...filters, direction: value || undefined });
  };

  const handleAssetClassToggle = (ac: string) => {
    const current = filters.asset_classes ?? [];
    const updated = current.includes(ac)
      ? current.filter((c) => c !== ac)
      : [...current, ac];
    onChange({ ...filters, asset_classes: updated.length ? updated : undefined });
  };

  const handleDateFrom = (value: string) => {
    onChange({ ...filters, opened_at_from: value || undefined });
  };

  const handleDateTo = (value: string) => {
    onChange({ ...filters, opened_at_to: value || undefined });
  };

  const handleTagToggle = (tagId: string) => {
    const current = filters.tag_ids ?? [];
    const updated = current.includes(tagId)
      ? current.filter((id) => id !== tagId)
      : [...current, tagId];
    onChange({ ...filters, tag_ids: updated.length ? updated : undefined });
  };

  const handlePlaybookChange = (value: string) => {
    onChange({ ...filters, playbook_id: value || undefined });
  };

  const handlePnlPositiveChange = (value: string) => {
    let pnl_positive: boolean | null = null;
    if (value === "true") pnl_positive = true;
    else if (value === "false") pnl_positive = false;
    onChange({ ...filters, pnl_positive });
  };

  const handleStatusChange = (value: string) => {
    const status = value === "open" || value === "closed" ? value : null;
    onChange({ ...filters, status });
  };

  const handleAccountChange = (value: string) => {
    onChange({ ...filters, account_id: value || undefined });
  };

  const handleClearAll = () => {
    setSymbolInput("");
    onChange(EMPTY_FILTERS);
  };

  const pnlPositiveValue =
    filters.pnl_positive === true
      ? "true"
      : filters.pnl_positive === false
      ? "false"
      : "";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
      {/* Toggle row */}
      <div className="flex items-center justify-between px-4 py-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:text-slate-100 transition-colors"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-4 h-4"
          >
            <line x1="4" y1="6" x2="20" y2="6" />
            <line x1="8" y1="12" x2="16" y2="12" />
            <line x1="11" y1="18" x2="13" y2="18" />
          </svg>
          Filters
          {activeCount > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold">
              {activeCount}
            </span>
          )}
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={handleClearAll}
            className="text-xs text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Active report-context chips (hour / weekday) — always visible */}
      {(filters.hour_of_day !== undefined && filters.hour_of_day !== null) ||
       (filters.day_of_week !== undefined && filters.day_of_week !== null) ? (
        <div className="px-4 pb-3 flex flex-wrap gap-2">
          {filters.hour_of_day !== undefined && filters.hour_of_day !== null && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
              Hour: {formatHour(filters.hour_of_day)}
              <button
                type="button"
                aria-label="Remove hour filter"
                onClick={() => onChange({ ...filters, hour_of_day: undefined })}
                className="ml-0.5 hover:text-blue-900 dark:hover:text-blue-100"
              >
                ×
              </button>
            </span>
          )}
          {filters.day_of_week !== undefined && filters.day_of_week !== null && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700">
              Day: {WEEKDAY_NAMES[filters.day_of_week] ?? filters.day_of_week}
              <button
                type="button"
                aria-label="Remove day filter"
                onClick={() => onChange({ ...filters, day_of_week: undefined })}
                className="ml-0.5 hover:text-blue-900 dark:hover:text-blue-100"
              >
                ×
              </button>
            </span>
          )}
        </div>
      ) : null}

      {/* Collapsible panel */}
      {open && (
        <div className="px-4 pb-4 border-t border-slate-200 dark:border-slate-700 pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {/* Symbol */}
          <div>
            <label className={LABEL_CLASS}>Symbol</label>
            <input
              type="text"
              value={symbolInput}
              onChange={(e) => handleSymbolChange(e.target.value)}
              placeholder="e.g. AAPL"
              className={INPUT_CLASS}
            />
          </div>

          {/* Direction */}
          <div>
            <label className={LABEL_CLASS}>Direction</label>
            <select
              value={filters.direction ?? ""}
              onChange={(e) => handleDirectionChange(e.target.value)}
              className={INPUT_CLASS}
            >
              <option value="">All</option>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
          </div>

          {/* Status */}
          <div>
            <label className={LABEL_CLASS}>Status</label>
            <select
              value={filters.status ?? ""}
              onChange={(e) => handleStatusChange(e.target.value)}
              className={INPUT_CLASS}
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          {/* Date range */}
          <div>
            <label className={LABEL_CLASS}>Opened From</label>
            <input
              type="date"
              value={filters.opened_at_from ?? ""}
              onChange={(e) => handleDateFrom(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Opened To</label>
            <input
              type="date"
              value={filters.opened_at_to ?? ""}
              onChange={(e) => handleDateTo(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>

          {/* Playbook */}
          <div>
            <label className={LABEL_CLASS}>Playbook</label>
            <select
              value={filters.playbook_id ?? ""}
              onChange={(e) => handlePlaybookChange(e.target.value)}
              className={INPUT_CLASS}
            >
              <option value="">All</option>
              {(playbooks ?? []).map((pb) => (
                <option key={pb.id} value={pb.id}>
                  {pb.name}
                </option>
              ))}
            </select>
          </div>

          {/* Account / Broker */}
          {accounts && accounts.length > 1 && (
            <div>
              <label className={LABEL_CLASS}>Account</label>
              <select
                value={filters.account_id ?? ""}
                onChange={(e) => handleAccountChange(e.target.value)}
                className={INPUT_CLASS}
              >
                <option value="">All</option>
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* PnL positive */}
          <div>
            <label className={LABEL_CLASS}>Result</label>
            <div className="flex gap-3 mt-2">
              {[
                { value: "", label: "All" },
                { value: "true", label: "Winners" },
                { value: "false", label: "Losers" },
              ].map((opt) => (
                <label key={opt.value} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="pnl_positive"
                    value={opt.value}
                    checked={pnlPositiveValue === opt.value}
                    onChange={(e) => handlePnlPositiveChange(e.target.value)}
                    className="accent-blue-500"
                  />
                  <span className="text-xs text-slate-700 dark:text-slate-300">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Asset classes */}
          <div className="sm:col-span-2">
            <label className={LABEL_CLASS}>Asset Class</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {ASSET_CLASSES.map((ac) => {
                const selected = filters.asset_classes?.includes(ac);
                return (
                  <button
                    key={ac}
                    type="button"
                    onClick={() => handleAssetClassToggle(ac)}
                    className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
                      selected
                        ? "bg-blue-600 border-blue-500 text-white"
                        : "bg-slate-100 dark:bg-slate-700 border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:border-slate-400 dark:border-slate-500"
                    }`}
                  >
                    {ac}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tags */}
          {tags && tags.length > 0 && (
            <div className="sm:col-span-2">
              <label className={LABEL_CLASS}>Tags</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {tags.map((tag) => {
                  const selected = filters.tag_ids?.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => handleTagToggle(tag.id)}
                      className={`transition-opacity ${selected ? "opacity-100 ring-2 ring-blue-500 ring-offset-1 ring-offset-slate-800 rounded-full" : "opacity-60 hover:opacity-90"}`}
                    >
                      <TagBadge tag={tag} />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
