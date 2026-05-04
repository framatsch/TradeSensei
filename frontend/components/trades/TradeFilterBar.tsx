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
import type { SavedTradeFilterRead } from "@/lib/types";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw } from "lucide-react";

export type { TradeFilters };

interface Props {
  filters: TradeFilters;
  onChange: (filters: TradeFilters) => void;
  /** The currently active saved view (if any). */
  activeView?: SavedTradeFilterRead;
  /** Opens the "Save as View" naming modal. */
  onSaveView?: () => void;
  /** Opens the "Rename View" modal. */
  onRenameView?: () => void;
  /** Overwrites the active User view with current filters. */
  onUpdateView?: () => void;
  /** Deletes the active User view after confirmation. */
  onDeleteView?: () => void;
  /** True while the update mutation is in flight. */
  isUpdating?: boolean;
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
  if (filters.closed_at_from) count++;
  if (filters.closed_at_to) count++;
  if (filters.tag_ids?.length) count++;
  if (filters.playbook_id) count++;
  if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) count++;
  if (filters.status) count++;
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
  closed_at_from: "",
  closed_at_to: "",
  tag_ids: [],
  playbook_id: "",
  pnl_positive: null,
  status: null,
  hour_of_day: undefined,
  day_of_week: undefined,
};

const WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatHour(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

/** Strip ISO timestamp suffix so <input type="date"> gets YYYY-MM-DD */
function toDateInputValue(value: string | undefined): string {
  if (!value) return "";
  return value.slice(0, 10); // "2024-01-01T00:00:00Z" → "2024-01-01"
}

const INPUT_CLASS =
  "w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary";
const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";

export function TradeFilterBar({ filters, onChange, activeView, onSaveView, onRenameView, onUpdateView, onDeleteView, isUpdating }: Props) {
  const [open, setOpen] = useState(() => countActiveFilters(filters) > 0);
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

  const handleClosedDateFrom = (value: string) => {
    onChange({ ...filters, closed_at_from: value || undefined });
  };

  const handleClosedDateTo = (value: string) => {
    onChange({ ...filters, closed_at_to: value || undefined });
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
    <div className="bg-card rounded-md border border-border shadow-sm">
      {/* Toggle row */}
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
          >
            {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            Filter
            {activeCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {activeCount}
              </span>
            )}
          </button>
          
          {activeView && (
            <div className="hidden sm:flex items-center gap-2 border-l pl-4 border-border/50">
              <span className="text-xs text-muted-foreground font-medium">View:</span>
              <span className="text-sm font-medium text-foreground">{activeView.name}</span>
            </div>
          )}
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-2">
          {onSaveView && (
            <button
              type="button"
              onClick={onSaveView}
              className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors px-3 py-1.5 bg-primary/10 rounded-md"
            >
              <Save className="w-3.5 h-3.5" />
              Save View
            </button>
          )}

          {/* Update View — only for active User views */}
          {activeView?.scope === "USER" && onUpdateView && (
            <button
              type="button"
              onClick={onUpdateView}
              disabled={isUpdating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-secondary text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 rounded-md"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              {isUpdating ? "Updating…" : "Update"}
            </button>
          )}

          {/* Rename View — only for active User views */}
          {activeView?.scope === "USER" && onRenameView && (
            <button
              type="button"
              onClick={onRenameView}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-secondary text-muted-foreground hover:text-foreground transition-colors rounded-md"
            >
              <Edit2 className="w-3.5 h-3.5" />
              Rename
            </button>
          )}

          {/* Delete View — only for active User views */}
          {activeView?.scope === "USER" && onDeleteView && (
            <button
              type="button"
              onClick={onDeleteView}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors rounded-md"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete View
            </button>
          )}

          {/* Clear Filters (always available if there are active filters) */}
          {activeCount > 0 && (
            <button
              type="button"
              onClick={handleClearAll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors rounded-md ml-2 border-l border-border/50 pl-4"
            >
              <X className="w-3.5 h-3.5" />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Collapsible panel */}
      {open && (
        <div className="p-4 border-t border-border">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">          {/* Symbol */}
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

          {/* Date range (Opened) */}
          <div>
            <label className={LABEL_CLASS}>Opened From</label>
            <input
              type="date"
              value={toDateInputValue(filters.opened_at_from)}
              onChange={(e) => handleDateFrom(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Opened To</label>
            <input
              type="date"
              value={toDateInputValue(filters.opened_at_to)}
              onChange={(e) => handleDateTo(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>

          {/* Date range (Closed) */}
          <div>
            <label className={LABEL_CLASS}>Closed From</label>
            <input
              type="date"
              value={toDateInputValue(filters.closed_at_from)}
              onChange={(e) => handleClosedDateFrom(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
          <div>
            <label className={LABEL_CLASS}>Closed To</label>
            <input
              type="date"
              value={toDateInputValue(filters.closed_at_to)}
              onChange={(e) => handleClosedDateTo(e.target.value)}
              className={INPUT_CLASS}
            />
          </div>

          {/* Hour of Day */}
          <div>
            <label className={LABEL_CLASS}>Hour of Day</label>
            <select
              value={filters.hour_of_day !== undefined && filters.hour_of_day !== null ? String(filters.hour_of_day) : ""}
              onChange={(e) => onChange({ ...filters, hour_of_day: e.target.value !== "" ? parseInt(e.target.value, 10) : undefined })}
              className={INPUT_CLASS}
            >
              <option value="">All hours</option>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{formatHour(i)}</option>
              ))}
            </select>
          </div>

          {/* Day of Week */}
          <div>
            <label className={LABEL_CLASS}>Day of Week</label>
            <select
              value={filters.day_of_week !== undefined && filters.day_of_week !== null ? String(filters.day_of_week) : ""}
              onChange={(e) => onChange({ ...filters, day_of_week: e.target.value !== "" ? parseInt(e.target.value, 10) : undefined })}
              className={INPUT_CLASS}
            >
              <option value="">All days</option>
              {WEEKDAY_NAMES.map((name, i) => (
                <option key={i} value={i}>{name}</option>
              ))}
            </select>
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
                    className="accent-primary"
                  />
                  <span className="text-xs text-muted-foreground">{opt.label}</span>
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
                    className={`px-3 py-1 rounded-md text-xs font-medium border transition-all duration-200 ${
                      selected
                        ? "bg-primary/15 border-primary/40 text-primary"
                        : "bg-secondary border-border text-muted-foreground hover:text-foreground hover:border-border/80"
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
                      className={`transition-opacity ${selected ? "opacity-100 ring-2 ring-primary ring-offset-1 ring-offset-background rounded-full" : "opacity-60 hover:opacity-90"}`}
                    >
                      <TagBadge tag={tag} />
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          </div>
        </div>
      )}
    </div>
  );
}
