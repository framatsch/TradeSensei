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
 * ReportFilterBar — collapsible global filter panel for the Reporting Hub.
 *
 * Contains:
 *  - Portfolio selector (single-select, exactly one required)
 *  - Date range picker (from / to)
 *  - Playbook multi-select dropdown
 *  - Tag multi-select dropdown
 *  - Trade status toggle (Closed Only / Include Open)
 *  - Collapse / expand toggle button
 */

"use client";

import { MetricHelpLink } from "@/components/ui/MetricHelpLink";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { AnnotationFilterRows, type AnnotationFilterRow } from "@/components/ui/AnnotationFilterRows";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import { usePortfolios } from "@/hooks/usePortfolios";
import { useAccounts } from "@/hooks/useAccounts";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useSavedViews, useSaveView, useUpdateView, useDeleteView } from "@/hooks/useReportingViews";
import { useWorkspaceFilter, useActivePortfolioId, type FilterConfig } from "@/components/workspace/WorkspaceFilterContext";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw, Filter as FilterIcon, Lock } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import type { DashboardFilterConfig } from "@/lib/api/types.gen";

import { SymbolTagInput } from "@/components/ui/SymbolTagInput";

const ASSET_CLASSES = ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"] as const;

// ─── Shared input style ───────────────────────────────────────────────────────

const INPUT_CLASS =
  "w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary";

const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";

// ─── Multi-select dropdown ────────────────────────────────────────────────────

interface MultiSelectProps {
  label: string;
  items: { id: string; name: string }[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  placeholder?: string;
}

function MultiSelect({
  label,
  items,
  selectedIds,
  onChange,
  placeholder = "Select...",
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleItem = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((i) => i !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectedNames = items
    .filter((item) => selectedIds.includes(item.id))
    .map((item) => item.name);

  return (
    <div className="relative" ref={ref}>
      <label className={LABEL_CLASS}>{label}</label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`${INPUT_CLASS} flex items-center justify-between text-left`}
      >
        <span className={selectedIds.length === 0 ? "text-muted-foreground" : ""}>
          {selectedIds.length === 0
            ? placeholder
            : `${selectedIds.length} selected`}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-muted-foreground transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-popover border border-border rounded-md shadow-lg max-h-48 overflow-y-auto">
          {items.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">No items</p>
          ) : (
            items.map((item) => {
              const isSelected = selectedIds.includes(item.id);
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => toggleItem(item.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-muted/60 transition-colors ${
                    isSelected ? "bg-primary/10 text-foreground" : "text-foreground"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    readOnly
                    className="w-4 h-4 rounded border-border accent-primary"
                  />
                  <span className="truncate">{item.name}</span>
                </button>
              );
            })
          )}
        </div>
      )}

      {/* Selected chips */}
      {selectedNames.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {selectedNames.map((name) => (
            <span
              key={name}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary"
            >
              {name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function WorkspaceFilterBar() {
  const [collapsed, setCollapsed] = useState(false);
  const showOpenTrades = useShowOpenTrades();

  const { filter, setFilter } = useWorkspaceFilter();
  const portfolioId = useActivePortfolioId();

  const dateFrom = filter.date_from;
  const dateTo = filter.date_to;
  const playbookIds = filter.playbook_ids || [];
  const tagIds = filter.taxonomy_ids || [];
  const accountIds = filter.account_ids || [];
  const symbols = filter.symbols || [];
  const excludedSymbols = filter.excluded_symbols || [];
  const assetClasses = filter.asset_classes || [];
  const status = filter.status;
  const viewId = filter.viewId;

  const setDateFrom = useCallback((date: string | null) => setFilter(prev => ({ ...prev, date_from: date })), [setFilter]);
  const setDateTo = useCallback((date: string | null) => setFilter(prev => ({ ...prev, date_to: date })), [setFilter]);
  const setPlaybookIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, playbook_ids: ids })), [setFilter]);
  const setTagIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, taxonomy_ids: ids })), [setFilter]);
  const setAccountIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, account_ids: ids })), [setFilter]);
  const setSymbols = useCallback((s: string[]) => setFilter(prev => ({ ...prev, symbols: s })), [setFilter]);
  const setExcludedSymbols = useCallback((s: string[]) => setFilter(prev => ({ ...prev, excluded_symbols: s })), [setFilter]);
  const setAssetClasses = useCallback((s: import("@/lib/api/types.gen").AssetClass[]) => setFilter(prev => ({ ...prev, asset_classes: s })), [setFilter]);
  const setStatus = useCallback((s: "open" | "closed" | null) => setFilter(prev => ({ ...prev, status: s })), [setFilter]);
  const setViewId = useCallback((id: string | null) => setFilter(prev => ({ ...prev, viewId: id })), [setFilter]);
    const setFilters = useCallback((f: Partial<FilterConfig>) => setFilter(prev => ({ 
    ...prev,
    date_from: f.date_from !== undefined ? f.date_from : prev.date_from,
    date_to: f.date_to !== undefined ? f.date_to : prev.date_to,
    playbook_ids: f.playbook_ids !== undefined ? f.playbook_ids : prev.playbook_ids,
    account_ids: f.account_ids !== undefined ? f.account_ids : prev.account_ids,
    taxonomy_ids: f.taxonomy_ids !== undefined ? f.taxonomy_ids : prev.taxonomy_ids,
    symbols: f.symbols !== undefined ? f.symbols : prev.symbols,
    excluded_symbols: f.excluded_symbols !== undefined ? f.excluded_symbols : prev.excluded_symbols,
    asset_classes: f.asset_classes !== undefined ? f.asset_classes : prev.asset_classes,
    status: f.status !== undefined ? f.status : prev.status,
    viewId: f.viewId !== undefined ? f.viewId : prev.viewId
  })), [setFilter]);
  const { data: accounts } = useAccounts(portfolioId ?? undefined);
  const { data: playbooks } = usePlaybooks();
  const { data: taxonomies } = useGetTaxonomies("trades");
  const { data: annotationDefs } = useGetAnnotationDefinitions();
  const tradeAnnotationDefs = (annotationDefs ?? []).filter(
    (d) => !d.is_archived && (d.scope === "trades" || d.scope === "both")
  );

  const handleAnnotationFiltersChange = useCallback(
    (rows: AnnotationFilterRow[]) => {
      if (viewId) setViewId(null);
      setFilter((prev) => ({ ...prev, annotation_filters: rows.length > 0 ? rows : [] }));
    },
    [viewId, setViewId, setFilter]
  );

  // ── Wrappers to clear viewId when manual filters change ──────────────
  const handleSetDateFrom = useCallback((val: string | null) => {
    if (viewId) setViewId(null);
    setDateFrom(val);
  }, [viewId, setViewId, setDateFrom]);

  const handleSetDateTo = useCallback((val: string | null) => {
    if (viewId) setViewId(null);
    setDateTo(val);
  }, [viewId, setViewId, setDateTo]);

  const handleSetPlaybookIds = useCallback((ids: string[]) => {
    if (viewId) setViewId(null);
    setPlaybookIds(ids);
  }, [viewId, setViewId, setPlaybookIds]);

  const handleSetTagIds = useCallback((ids: string[]) => {
    if (viewId) setViewId(null);
    setTagIds(ids);
  }, [viewId, setViewId, setTagIds]);

  const handleSetSymbolsAndExcluded = useCallback((inc: string[], exc: string[]) => {
    if (viewId) setViewId(null);
    setSymbols(inc);
    setExcludedSymbols(exc);
  }, [viewId, setViewId, setSymbols, setExcludedSymbols]);

  const handleAssetClassToggle = useCallback((ac: import("@/lib/api/types.gen").AssetClass) => {
    if (viewId) setViewId(null);
    const current = assetClasses;
    const updated = current.includes(ac) ? current.filter((c) => c !== ac) : [...current, ac];
    setAssetClasses(updated);
  }, [viewId, setViewId, assetClasses, setAssetClasses]);

  const handleSetStatus = useCallback((val: "open" | "closed" | null) => {
    if (viewId) setViewId(null);
    setStatus(val);
  }, [viewId, setViewId, setStatus]);

  // ── Saved views logic ────────────────────────────────────────────────────
  const { data: savedViews } = useSavedViews(portfolioId);
  const saveViewMutation = useSaveView(portfolioId);
  const updateViewMutation = useUpdateView(portfolioId);
  const deleteViewMutation = useDeleteView(portfolioId);

  const [saveViewName, setSaveViewName] = useState("");
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const activeView = useMemo(() => {
    if (!viewId || !savedViews) return null;
    return savedViews.find((v) => v.id === viewId) || null;
  }, [viewId, savedViews]);


  const activeCount = useMemo(() => {
    let count = 0;
    if (activeView) {
      const cfg = activeView.filter_config;
      if (cfg.playbook_ids && cfg.playbook_ids.length > 0) count++;
      if (cfg.account_ids && cfg.account_ids.length > 0) count++;
      if (cfg.symbols && cfg.symbols.length > 0) count++;
      if (cfg.excluded_symbols && cfg.excluded_symbols.length > 0) count++;
      if (cfg.asset_classes && cfg.asset_classes.length > 0) count++;
      if (cfg.date_from || cfg.date_to) count++;
      if (cfg.status) count++;
      return count;
    }
    
    if (playbookIds && playbookIds.length > 0) count++;
    if (tagIds && tagIds.length > 0) count++;
    if (accountIds && accountIds.length > 0) count++;
    if (symbols.length > 0) count++;
    if (excludedSymbols.length > 0) count++;
    if (assetClasses.length > 0) count++;
    if (dateFrom || dateTo) count++;
    if (status) count++;
    return count;
  }, [playbookIds, tagIds, accountIds, dateFrom, dateTo, status, activeView, symbols, excludedSymbols, assetClasses]);

  const filterConfig = useMemo(() => {
    const config: DashboardFilterConfig = {};
    if (dateFrom) config.date_from = dateFrom;
    if (dateTo) config.date_to = dateTo;
    if (playbookIds.length > 0) config.playbook_ids = playbookIds;
    if (accountIds.length > 0) config.account_ids = accountIds;
    if (tagIds.length > 0) config.taxonomy_ids = tagIds;
    if (symbols.length > 0) config.symbols = symbols;
    if (excludedSymbols.length > 0) config.excluded_symbols = excludedSymbols;
    if (assetClasses.length > 0) config.asset_classes = assetClasses;
    if (status) config.status = status;
    return config;
  }, [dateFrom, dateTo, playbookIds, tagIds, accountIds, status, symbols, excludedSymbols, assetClasses]);

  const handleSaveView = useCallback(() => {
    if (!saveViewName.trim() || !portfolioId) return;
    saveViewMutation.mutate(
      {
        name: saveViewName.trim(),
        filter_config: filterConfig,
      },
      {
        onSuccess: (newView) => {
          setViewId(newView.id);
          setSaveViewName("");
          setShowSaveModal(false);
        },
      },
    );
  }, [saveViewName, portfolioId, filterConfig, saveViewMutation, setViewId]);

  const handleUpdateView = useCallback(() => {
    if (!viewId || !portfolioId) return;
    updateViewMutation.mutate({
      viewId,
      payload: { filter_config: filterConfig }
    });
  }, [viewId, portfolioId, filterConfig, updateViewMutation]);

  const handleRenameView = useCallback(() => {
    if (!saveViewName.trim() || !portfolioId || !viewId) return;
    updateViewMutation.mutate(
      {
        viewId,
        payload: { name: saveViewName.trim() },
      },
      {
        onSuccess: () => {
          setSaveViewName("");
          setShowRenameModal(false);
        },
      },
    );
  }, [saveViewName, portfolioId, viewId, updateViewMutation]);

  const handleDeleteView = useCallback(
    (id: string) => {
      deleteViewMutation.mutate(id, {
        onSuccess: () => {
          if (viewId === id) {
            setViewId(null);
          }
          setDeleteConfirmId(null);
        },
      });
    },
    [deleteViewMutation, viewId, setViewId],
  );

  const handleViewSelect = useCallback(
    (id: string) => {
      const view = savedViews?.find((v) => v.id === id);
      if (view) {
        setViewId(view.id);
        setFilters({
          date_from: view.filter_config.date_from ?? null,
          date_to: view.filter_config.date_to ?? null,
          playbook_ids: view.filter_config.playbook_ids ?? [],
          account_ids: view.filter_config.account_ids ?? [],
          taxonomy_ids: view.filter_config.taxonomy_ids ?? [],
          symbols: view.filter_config.symbols ?? [],
          excluded_symbols: view.filter_config.excluded_symbols ?? [],
          asset_classes: view.filter_config.asset_classes ?? [],
          status: view.filter_config.status ?? null,
        });
      }
    },
    [savedViews, setViewId, setFilters],
  );

  // handlePortfolioChange removed since it's global

  return (
    <div className="w-full bg-card border border-border rounded-md shadow-sm">
      {/* Header bar with toggle */}
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            Filters
            {activeCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {activeCount}
              </span>
            )}
          </button>

          {/* Portfolio dropdown removed. Handled globally via title bar. */}

          {/* Views Dropdown */}
          <div className="hidden sm:flex items-center gap-2 border-l pl-4 border-border/50">
            <span className="text-xs font-medium text-muted-foreground">Saved View</span>
            {savedViews && savedViews.length > 0 ? (
              <select
                value={viewId ?? ""}
                onChange={(e) => handleViewSelect(e.target.value)}
                className="w-40 px-2 py-1.5 bg-secondary border border-border rounded-md text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="" disabled>Select view...</option>
                {savedViews.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-xs text-muted-foreground italic">No saved views</span>
            )}
          </div>
        </div>

        {/* Save Controls in Header */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setSaveViewName("");
              setShowSaveModal(true);
            }}
            className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors px-3 py-1.5 bg-primary/10 rounded-md"
          >
            <Save className="w-3.5 h-3.5" />
            Save View
          </button>

          {activeView && (
            <button
              type="button"
              onClick={handleUpdateView}
              disabled={updateViewMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-secondary text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50 rounded-md"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              {updateViewMutation.isPending ? "Updating…" : "Update"}
            </button>
          )}

          {activeView && (
            <button
              type="button"
              onClick={() => {
                setSaveViewName(activeView.name);
                setShowRenameModal(true);
              }}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-secondary text-muted-foreground hover:text-foreground transition-colors rounded-md"
            >
              <Edit2 className="w-3.5 h-3.5" />
              Rename
            </button>
          )}

          {activeView && (
            deleteConfirmId === activeView.id ? (
              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-[color-mix(in_srgb,var(--destructive)_10%,transparent)]">
                <span className="text-destructive">Are you sure?</span>
                <button
                  type="button"
                  onClick={() => handleDeleteView(activeView.id)}
                  disabled={deleteViewMutation.isPending}
                  className="px-2 py-0.5 bg-destructive text-white rounded hover:bg-destructive/90 transition-colors"
                >
                  Yes
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteConfirmId(null)}
                  className="px-2 py-0.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setDeleteConfirmId(activeView.id)}
                disabled={deleteViewMutation.isPending}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-[color-mix(in_srgb,var(--destructive)_10%,transparent)] transition-colors rounded-md disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete View
              </button>
            )
          )}
          {/* Clear Filters (always available if there are active filters) */}
          {((playbookIds.length > 0 ||
            tagIds.length > 0 ||
            accountIds.length > 0 ||
            symbols.length > 0 ||
            excludedSymbols.length > 0 ||
            assetClasses.length > 0 ||
            dateFrom ||
            dateTo ||
            status) ? 1 : 0) > 0 && (
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
                onClick={() => {
                  setDateFrom(null);
                  setDateTo(null);
                  setPlaybookIds([]);
                  setTagIds([]);
                  setAccountIds([]);
                  setSymbols([]);
                  setExcludedSymbols([]);
                  setAssetClasses([]);
                  setStatus(null);
                }}
              >
                Clear all
              </button>
          )}
        </div>
      </div>

      {/* Collapsible filter body */}
      {!collapsed && (
        <div className="p-4 border-t border-border">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {/* Date from */}
            <div>
              <label className={LABEL_CLASS}>Date From</label>
              <input
                type="date"
                value={dateFrom ?? ""}
                onChange={(e) => handleSetDateFrom(e.target.value || null)}
                className={INPUT_CLASS}
              />
            </div>

            {/* Date to */}
            <div>
              <label className={LABEL_CLASS}>Date To</label>
              <input
                type="date"
                value={dateTo ?? ""}
                onChange={(e) => handleSetDateTo(e.target.value || null)}
                className={INPUT_CLASS}
              />
            </div>

            {/* Account multi-select */}
            <MultiSelect
              label="Accounts"
              items={accounts ?? []}
              selectedIds={accountIds}
              onChange={(ids) => {
                if (viewId) setViewId(null);
                setAccountIds(ids);
              }}
              placeholder="All"
            />

            {/* Playbook multi-select */}
            <MultiSelect
              label="Playbooks"
              items={playbooks ?? []}
              selectedIds={playbookIds}
              onChange={handleSetPlaybookIds}
            />

            {/* Taxonomy multi-select */}
            <MultiSelect
              label="Taxonomies"
              items={taxonomies ?? []}
              selectedIds={tagIds}
              onChange={handleSetTagIds}
            />

            {/* Trade status toggle */}
            {showOpenTrades && (
              <div>
                <label className={`${LABEL_CLASS} flex items-center gap-1.5`}>
                  Trade Status
                  <MetricHelpLink anchor="open-closed-filter" />
                </label>
                <div className="flex items-center gap-3 pt-1">
                  <button
                    type="button"
                    title="Closed trades only"
                    onClick={() => handleSetStatus(status === "closed" ? null : "closed")}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                      status === "closed"
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Closed
                  </button>
                  <button
                    type="button"
                    title="Open trades only"
                    onClick={() => handleSetStatus(status === "open" ? null : "open")}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap ${
                      status === "open"
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Open
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Annotation Filters — full width */}
          {tradeAnnotationDefs.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border/50">
              <label className={LABEL_CLASS}>Annotation Filters</label>
              <div className="mt-1">
                <AnnotationFilterRows
                  rows={filter.annotation_filters ?? []}
                  definitions={tradeAnnotationDefs}
                  onChange={handleAnnotationFiltersChange}
                />
              </div>
            </div>
          )}

          {/* Symbol + Asset Class — always visible */}
          <div className="mt-4 pt-4 border-t border-border/50 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {/* Symbol */}
            <div className="sm:col-span-2">
              <label className={LABEL_CLASS}>Symbol</label>
              <SymbolTagInput
                included={symbols}
                excluded={excludedSymbols}
                onChange={handleSetSymbolsAndExcluded}
              />
            </div>

            {/* Asset classes */}
            <div className="sm:col-span-3">
              <label className={LABEL_CLASS}>Asset Class</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {ASSET_CLASSES.map((ac) => {
                  const selected = assetClasses.includes(ac);
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
          </div>
        </div>
      )}

      {/* Save View Modal */}
      <Dialog.Root open={showSaveModal} onOpenChange={(open: boolean) => {
        setShowSaveModal(open);
        if (!open) setSaveViewName("");
      }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-xl bg-card border border-border p-6 shadow-2xl">
            <Dialog.Title className="mb-4 text-base font-semibold text-foreground">Save Current View</Dialog.Title>
            <label className="mb-2 block text-sm font-medium text-[color-mix(in_srgb,var(--muted-foreground)_100%,transparent)]">View Name</label>
            <input
              type="text"
              className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="View name..."
              value={saveViewName}
              onChange={(e) => setSaveViewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSaveView()}
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowSaveModal(false);
                  setSaveViewName("");
                }}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!saveViewName.trim() || saveViewMutation.isPending}
                onClick={handleSaveView}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
              >
                {saveViewMutation.isPending ? "Saving…" : "Save View"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Rename View Modal */}
      <Dialog.Root open={showRenameModal} onOpenChange={(open: boolean) => {
        setShowRenameModal(open);
        if (!open) setSaveViewName("");
      }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-xl bg-card border border-border p-6 shadow-2xl">
            <Dialog.Title className="mb-4 text-base font-semibold text-foreground">Rename View</Dialog.Title>
            <input
              type="text"
              className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={saveViewName}
              onChange={(e) => setSaveViewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRenameView()}
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRenameModal(false);
                  setSaveViewName("");
                }}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!saveViewName.trim() || updateViewMutation.isPending}
                onClick={handleRenameView}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
              >
                {updateViewMutation.isPending ? "Saving…" : "Save"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
