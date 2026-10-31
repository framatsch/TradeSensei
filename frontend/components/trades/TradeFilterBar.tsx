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

import { Fragment, useEffect, useId, useRef, useState, useCallback, type ReactNode } from "react";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw, SlidersHorizontal } from "lucide-react";
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
import { countActiveFilters, DESKTOP_FILTER_FIELDS, type FilterFieldKey } from "@/lib/tradeFilterFields";
import { TradeFilterSheet } from "./TradeFilterSheet";

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
  "w-full min-w-0 px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary";
const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";
const DATE_LABELS = {
  opened_at_from: "Opened From",
  opened_at_to: "Opened To",
  closed_at_from: "Closed From",
  closed_at_to: "Closed To",
};

interface AccountMultiSelectProps {
  accounts: Account[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  isLoading?: boolean;
  variant?: "popover" | "inline";
}

function AccountMultiSelect({ accounts, selectedIds, onChange, isLoading = false, variant = "popover" }: AccountMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (e.target instanceof Node && ref.current && !ref.current.contains(e.target)) {
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
      <label htmlFor={id} className={LABEL_CLASS}>Account</label>
      <button
        id={id}
        type="button"
        onClick={() => setOpen((value) => !value)}
        disabled={isLoading}
        aria-expanded={open}
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
        <div className={`${variant === "inline" ? "relative" : "absolute z-50"} mt-1 w-full max-h-56 overflow-y-auto rounded-md border border-border bg-popover shadow-lg`}>
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
  const [sheetOpen, setSheetOpen] = useState(false);
  const fieldId = useId();
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

  const renderField = (key: FilterFieldKey, variant: "popover" | "inline" = "popover"): ReactNode => {
    const id = `${fieldId}-${variant}-${key}`;
    switch (key) {
      case "symbols":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Symbol</label>
            <SymbolTagInput
              id={id}
              included={filters.symbols ?? []}
              excluded={filters.excluded_symbols ?? []}
              onChange={(included, excluded) => onChange({ ...filters, symbols: included.length ? included : undefined, excluded_symbols: excluded.length ? excluded : undefined })}
            />
          </div>
        );
      case "direction":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Direction</label>
            <select id={id} value={filters.direction ?? ""} onChange={(event) => handleDirectionChange(event.target.value)} className={INPUT_CLASS}>
              <option value="">All</option><option value="LONG">LONG</option><option value="SHORT">SHORT</option>
            </select>
          </div>
        );
      case "status":
        return showOpenTrades ? (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Status</label>
            <select id={id} value={filters.status ?? ""} onChange={(event) => handleStatusChange(event.target.value)} className={INPUT_CLASS}>
              <option value="">All</option><option value="open">Open</option><option value="closed">Closed</option>
            </select>
          </div>
        ) : null;
      case "opened_at_from":
      case "opened_at_to":
      case "closed_at_from":
      case "closed_at_to":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>{DATE_LABELS[key]}</label>
            <input id={id} type="date" value={toDateInputValue(filters[key])} onChange={(event) => onChange({ ...filters, [key]: event.target.value || undefined })} className={`${INPUT_CLASS} font-mono lg:font-sans`} />
          </div>
        );
      case "hour_of_day":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Hour of Day</label>
            <select id={id} value={filters.hour_of_day ?? ""} onChange={(event) => onChange({ ...filters, hour_of_day: event.target.value !== "" ? Number(event.target.value) : undefined })} className={`${INPUT_CLASS} font-mono lg:font-sans`}>
              <option value="">All hours</option>
              {Array.from({ length: 24 }, (_, hour) => <option key={hour} value={hour}>{formatHour(hour)}</option>)}
            </select>
          </div>
        );
      case "day_of_week":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Day of Week</label>
            <select id={id} value={filters.day_of_week ?? ""} onChange={(event) => onChange({ ...filters, day_of_week: event.target.value !== "" ? Number(event.target.value) : undefined })} className={INPUT_CLASS}>
              <option value="">All days</option>
              {WEEKDAY_NAMES.map((day, index) => <option key={day} value={index}>{day}</option>)}
            </select>
          </div>
        );
      case "account_ids":
        return <AccountMultiSelect accounts={accounts} selectedIds={filters.account_ids ?? []} onChange={handleAccountChange} isLoading={isLoadingAccountOptions} variant={variant} />;
      case "playbook_id":
        return (
          <div>
            <label htmlFor={id} className={LABEL_CLASS}>Playbook</label>
            <select id={id} value={filters.playbook_id ?? ""} onChange={(event) => handlePlaybookChange(event.target.value)} className={INPUT_CLASS}>
              <option value="">All</option>
              {(playbooks ?? []).map((playbook) => <option key={playbook.id} value={playbook.id}>{playbook.name}</option>)}
            </select>
          </div>
        );
      case "pnl_positive":
        return (
          <div>
            <span id={id} className={LABEL_CLASS}>Result</span>
            <div className="flex gap-3 mt-2" role="radiogroup" aria-labelledby={id}>
              {[{ value: "", label: "All" }, { value: "true", label: "Winners" }, { value: "false", label: "Losers" }].map((option) => (
                <label key={option.value} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="radio" name={id} value={option.value} checked={pnlPositiveValue === option.value} onChange={(event) => handlePnlPositiveChange(event.target.value)} className="accent-primary" />
                  <span className="text-xs text-muted-foreground">{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        );
      case "asset_classes":
        return (
          <div className={variant === "inline" ? undefined : "sm:col-span-2"}>
            <span className={LABEL_CLASS}>Asset Class</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {ASSET_CLASSES.map((assetClass) => (
                <button key={assetClass} type="button" onClick={() => handleAssetClassToggle(assetClass)} aria-pressed={!!filters.asset_classes?.includes(assetClass)} className={`px-3 py-1 rounded-md text-xs font-medium border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${filters.asset_classes?.includes(assetClass) ? "bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] border-[color-mix(in_srgb,var(--primary)_40%,transparent)] text-primary" : "bg-secondary border-border text-muted-foreground hover:text-foreground"}`}>
                  {assetClass}
                </button>
              ))}
            </div>
          </div>
        );
      case "execution_state":
        return (
          <div className={variant === "inline" ? undefined : "sm:col-span-2"}>
            <span className={LABEL_CLASS}>Execution State</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {EXECUTION_STATES.map((state) => (
                <button key={state.value} type="button" onClick={() => handleExecutionStateToggle(state.value)} aria-pressed={!!filters.execution_state?.includes(state.value)} className={`px-3 py-1 rounded-md text-xs font-medium border transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${filters.execution_state?.includes(state.value) ? "bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] border-[color-mix(in_srgb,var(--primary)_40%,transparent)] text-primary" : "bg-secondary border-border text-muted-foreground hover:text-foreground"}`}>
                  {state.label}
                </button>
              ))}
            </div>
          </div>
        );
      case "has_unlinked_executions":
        return (
          <div>
            <span className={LABEL_CLASS}>Needs linking</span>
            <div className="mt-2">
              <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" checked={filters.has_unlinked_executions === true} onChange={(event) => onChange({ ...filters, has_unlinked_executions: event.target.checked ? true : undefined })} className="accent-primary" />
                Show only trades with unresolved execution linking
              </label>
            </div>
          </div>
        );
      case "taxonomy_ids":
        return taxonomies && taxonomies.length > 0 ? (
          <div className={variant === "inline" ? undefined : "sm:col-span-2"}>
            <span className={LABEL_CLASS}>Taxonomies</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {taxonomies.map((taxonomy) => (
                <button key={taxonomy.id} type="button" onClick={() => handleTaxonomyToggle(taxonomy.id)} aria-pressed={!!filters.taxonomy_ids?.includes(taxonomy.id)} className={`transition-opacity ${filters.taxonomy_ids?.includes(taxonomy.id) ? "opacity-100 ring-2 ring-primary ring-offset-1 ring-offset-background rounded-full" : "opacity-60 hover:opacity-90"}`}>
                  <TaxonomyBadge taxonomy={taxonomy} />
                </button>
              ))}
            </div>
          </div>
        ) : null;
      case "annotation_filters":
        return tradeAnnotationDefs.length > 0 ? (
          <div className={variant === "inline" ? "[&>div>div]:max-w-full [&>div>div]:flex-wrap" : "mt-4 pt-4 border-t"}>
            <span className={`${LABEL_CLASS} mb-1.5`}>Annotation Filters</span>
            <AnnotationFilterRows rows={filters.annotation_filters ?? []} definitions={tradeAnnotationDefs} onChange={handleAnnotationFiltersChange} />
          </div>
        ) : null;
    }
  };

  return (
    <div className="solid-card shadow-sm mb-4">
      {/* Toggle row */}
      <div className="hidden items-center justify-between p-3 lg:flex" data-testid="trade-desktop-filter-toolbar">
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
        <div className="hidden p-4 border-t border-border lg:block" data-testid="trade-desktop-filters">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {DESKTOP_FILTER_FIELDS.filter((key) => key !== "annotation_filters").map((key) => <Fragment key={key}>{renderField(key)}</Fragment>)}
          </div>
          {renderField("annotation_filters")}
        </div>
      )}
      <div className="flex min-w-0 items-center gap-2 p-3 lg:hidden" data-testid="trade-mobile-filter-toolbar">
        <TradeFilterSheet
          open={sheetOpen}
          onOpenChange={setSheetOpen}
          filters={filters}
          renderField={(key) => renderField(key, "inline")}
          onClear={handleClearAll}
          activeView={activeView}
          onSaveView={onSaveView}
          onUpdateView={onUpdateView}
          onRenameView={onRenameView}
          onDeleteView={onDeleteView}
          isUpdating={isUpdating}
          trigger={(
            <button type="button" className="btn-ghost min-h-10 shrink-0 gap-1.5 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Filter{activeCount > 0 && <span className="font-mono">({activeCount})</span>}
            </button>
          )}
        />
        {activeView && <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground" title={`View: ${activeView.name}`}>View: <span className="font-medium text-foreground">{activeView.name}</span></span>}
        {activeCount > 0 && <button type="button" onClick={handleClearAll} className="ml-auto min-h-10 shrink-0 rounded-md px-2 text-xs text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Clear</button>}
      </div>
    </div>
  );
}
