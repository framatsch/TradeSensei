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
 * TradeFilterBar — collapsible filter panel for the trades list.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw } from "lucide-react";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useAccounts } from "@/hooks/useAccounts";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { TaxonomyBadge } from "@/components/trades/TaxonomyBadge";
import { SymbolTagInput } from "@/components/ui/SymbolTagInput";
import type { TradeFilters } from "@/hooks/useTrades";
import type { Account, SavedTradeFilterRead } from "@/lib/types";
import { AnnotationFilterRows, type AnnotationFilterRow } from "@/components/ui/AnnotationFilterRows";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";

export type { TradeFilters };

interface Props {
  filters: TradeFilters;
  onChange: (filters: TradeFilters) => void;
  showOpenTrades?: boolean;
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

const ASSET_CLASSES = ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO", "COMBO"] as const;
const EXECUTION_STATES = [
  { value: "manual", label: "Manual" },
  { value: "edited", label: "Edited" },
  { value: "imported", label: "Imported" },
] as const;

/** Count how many filter fields are non-empty. */
function countActiveFilters(filters: TradeFilters): number {
  let count = 0;
  if (filters.symbols?.length) count++;
  if (filters.excluded_symbols?.length) count++;
  if (filters.direction) count++;
  if (filters.asset_classes?.length) count++;
  if (filters.opened_at_from) count++;
  if (filters.opened_at_to) count++;
  if (filters.closed_at_from) count++;
  if (filters.closed_at_to) count++;
  if (filters.taxonomy_ids?.length) count++;
  if (filters.account_ids?.length) count++;
  if (filters.playbook_id) count++;
  if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) count++;
  if (filters.status) count++;
  if (filters.hour_of_day !== undefined && filters.hour_of_day !== null) count++;
  if (filters.day_of_week !== undefined && filters.day_of_week !== null) count++;
  if (filters.annotation_filters?.length) count++;
  if (filters.execution_state?.length) count++;
  if (filters.has_unlinked_executions !== undefined) count++;
  return count;
}

const EMPTY_FILTERS: TradeFilters = {
  symbols: [],
  excluded_symbols: [],
  direction: "",
  asset_classes: [],
  opened_at_from: "",
  opened_at_to: "",
  closed_at_from: "",
  closed_at_to: "",
  taxonomy_ids: [],
  account_ids: [],
  playbook_id: "",
  pnl_positive: null,
  status: null,
  hour_of_day: undefined,
  day_of_week: undefined,
  annotation_filters: [],
  execution_state: [],
  has_unlinked_executions: undefined,
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

interface AccountMultiSelectProps {
  accounts: Account[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  isLoading?: boolean;
}

function AccountMultiSelect({ accounts, selectedIds, onChange, isLoading = false }: AccountMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selectedAccounts = accounts.filter((account) => selectedIds.includes(account.id));

  const toggleAccount = (accountId: string) => {
    if (selectedIds.includes(accountId)) {
      onChange(selectedIds.filter((id) => id !== accountId));
      return;
    }
    onChange([...selectedIds, accountId]);
  };

  return (
    <div className="relative" ref={ref}>
      <label className={LABEL_CLASS}>Account</label>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        disabled={isLoading}
        className={`${INPUT_CLASS} flex items-center justify-between gap-2 text-left disabled:opacity-60`}
      >
        <span className={selectedIds.length === 0 ? "text-muted-foreground" : ""}>
          {isLoading
            ? "Loading accounts…"
            : selectedIds.length === 0
            ? "All Accounts"
            : `${selectedIds.length} selected`}
        </span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-56 overflow-y-auto rounded-md border border-border bg-popover shadow-lg">
          {accounts.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              {isLoading ? "Loading accounts…" : "No accounts available"}
            </p>
          ) : (
            <>
              {accounts.map((account) => {
                const isSelected = selectedIds.includes(account.id);
                return (
                  <button
                    key={account.id}
                    type="button"
                    onClick={() => toggleAccount(account.id)}
                    className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-muted/60 ${
                      isSelected ? "bg-primary/10 text-foreground" : "text-foreground"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      readOnly
                      className="h-4 w-4 rounded border-border accent-primary"
                    />
                    <span className="truncate">
                      {account.name}
                      {account.account_number ? ` (${account.account_number})` : ""}
                    </span>
                  </button>
                );
              })}
              <div className="border-t border-border p-2">
                <button
                  type="button"
                  onClick={() => onChange([])}
                  disabled={selectedIds.length === 0}
                  className="w-full rounded-md px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50"
                >
                  Clear selection
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {selectedAccounts.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {selectedAccounts.map((account) => (
            <span
              key={account.id}
              className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary"
            >
              {account.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function TradeFilterBar({ filters, onChange, showOpenTrades = true, activeView, onSaveView, onRenameView, onUpdateView, onDeleteView, isUpdating }: Props) {
  const [open, setOpen] = useState(() => countActiveFilters(filters) > 0);
  const activeCount = countActiveFilters(filters);

  const { activePortfolioId, isLoading: isPortfolioLoading } = useActivePortfolio();
  const { data: taxonomies } = useGetTaxonomies("trades");
  const { data: playbooks } = usePlaybooks();
  const { data: accounts = [], isLoading: isLoadingAccounts } = useAccounts(activePortfolioId ?? undefined);
  const isLoadingAccountOptions = isPortfolioLoading || isLoadingAccounts;
  const { data: annotationDefs } = useGetAnnotationDefinitions();
  const tradeAnnotationDefs = (annotationDefs ?? []).filter(
    (d) => !d.is_archived && (d.scope === "trades" || d.scope === "both")
  );

  const handleAnnotationFiltersChange = useCallback(
    (rows: AnnotationFilterRow[]) => {
      onChange({ ...filters, annotation_filters: rows.length > 0 ? rows : undefined });
    },
    [filters, onChange]
  );

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

  const handleTaxonomyToggle = (taxonomyId: string) => {
    const current = filters.taxonomy_ids ?? [];
    const updated = current.includes(taxonomyId)
      ? current.filter((id) => id !== taxonomyId)
      : [...current, taxonomyId];
    onChange({ ...filters, taxonomy_ids: updated.length ? updated : undefined });
  };

  const handleAccountChange = (accountIds: string[]) => {
    onChange({ ...filters, account_ids: accountIds.length > 0 ? accountIds : undefined });
  };

  const handlePlaybookChange = (value: string) => {
    onChange({ ...filters, playbook_id: value || undefined });
  };

  const handleExecutionStateToggle = (executionState: "manual" | "edited" | "imported") => {
    const current = filters.execution_state ?? [];
    const updated = current.includes(executionState)
      ? current.filter((state) => state !== executionState)
      : [...current, executionState];
    onChange({ ...filters, execution_state: updated.length ? updated : undefined });
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
    onChange(EMPTY_FILTERS);
  };

  const pnlPositiveValue =
    filters.pnl_positive === true
      ? "true"
      : filters.pnl_positive === false
      ? "false"
      : "";

  return (
    <div className="solid-card shadow-sm mb-4">
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
            <SymbolTagInput
              included={filters.symbols ?? []}
              excluded={filters.excluded_symbols ?? []}
              onChange={(included, excluded) => {
                onChange({
                  ...filters,
                  symbols: included.length > 0 ? included : undefined,
                  excluded_symbols: excluded.length > 0 ? excluded : undefined,
                });
              }}
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
          {showOpenTrades && (
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
          )}

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

          {/* Account */}
          <AccountMultiSelect
            accounts={accounts}
            selectedIds={filters.account_ids ?? []}
            onChange={handleAccountChange}
            isLoading={isLoadingAccountOptions}
          />

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
                const selected = !!filters.asset_classes?.includes(ac);
                return (
                  <button
                    key={ac}
                    type="button"
                    onClick={() => handleAssetClassToggle(ac)}
                    aria-pressed={selected}
                    className={`px-3 py-1 rounded-md text-xs font-medium border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      selected
                        ? "bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] border-[color-mix(in_srgb,var(--primary)_40%,transparent)] text-primary"
                        : "bg-secondary border-border text-muted-foreground hover:text-foreground hover:border-border/80"
                    }`}
                  >
                    {ac}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Execution state */}
          <div className="sm:col-span-2">
            <label className={LABEL_CLASS}>Execution State</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {EXECUTION_STATES.map((state) => {
                const selected = !!filters.execution_state?.includes(state.value);
                return (
                  <button
                    key={state.value}
                    type="button"
                    onClick={() => handleExecutionStateToggle(state.value)}
                    aria-pressed={selected}
                    className={`px-3 py-1 rounded-md text-xs font-medium border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                      selected
                        ? "bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] border-[color-mix(in_srgb,var(--primary)_40%,transparent)] text-primary"
                        : "bg-secondary border-border text-muted-foreground hover:text-foreground hover:border-border/80"
                    }`}
                  >
                    {state.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className={LABEL_CLASS}>Needs linking</label>
            <div className="mt-2">
              <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_unlinked_executions === true}
                  onChange={(e) =>
                    onChange({
                      ...filters,
                      has_unlinked_executions: e.target.checked ? true : undefined,
                    })
                  }
                  className="accent-primary"
                />
                Show only trades with unresolved execution linking
              </label>
            </div>
          </div>

          {/* Taxonomies */}
          {taxonomies && taxonomies.length > 0 && (
            <div className="sm:col-span-2">
              <label className={LABEL_CLASS}>Taxonomies</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {taxonomies.map((taxonomy) => {
                  const selected = filters.taxonomy_ids?.includes(taxonomy.id);
                  return (
                    <button
                      key={taxonomy.id}
                      type="button"
                      onClick={() => handleTaxonomyToggle(taxonomy.id)}
                      className={`transition-opacity ${selected ? "opacity-100 ring-2 ring-primary ring-offset-1 ring-offset-background rounded-full" : "opacity-60 hover:opacity-90"}`}
                    >
                      <TaxonomyBadge taxonomy={taxonomy} />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          </div>

          {/* Annotation Filters — full width below grid */}
          {tradeAnnotationDefs.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border/50">
              <label className={`${LABEL_CLASS} mb-1.5`}>Annotation Filters</label>
              <AnnotationFilterRows
                rows={filters.annotation_filters ?? []}
                definitions={tradeAnnotationDefs}
                onChange={handleAnnotationFiltersChange}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
