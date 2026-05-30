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
import { usePortfolios } from "@/hooks/usePortfolios";
import { useAccounts } from "@/hooks/useAccounts";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useSavedViews, useSaveView, useUpdateView, useDeleteView } from "@/hooks/useReportingViews";
import { useWorkspaceFilter, useActivePortfolioId } from "@/components/workspace/WorkspaceFilterContext";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw, Filter as FilterIcon, Lock } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import type { DashboardFilterConfig } from "@/lib/api/types.gen";

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
  const status = (filter as any).status as "open" | "closed" | null;
  const viewId = filter.viewId;

  const setDateFrom = useCallback((date: string | null) => setFilter(prev => ({ ...prev, date_from: date })), [setFilter]);
  const setDateTo = useCallback((date: string | null) => setFilter(prev => ({ ...prev, date_to: date })), [setFilter]);
  const setPlaybookIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, playbook_ids: ids })), [setFilter]);
  const setTagIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, taxonomy_ids: ids })), [setFilter]);
  const setAccountIds = useCallback((ids: string[]) => setFilter(prev => ({ ...prev, account_ids: ids })), [setFilter]);
  const setStatus = useCallback((s: "open" | "closed" | null) => setFilter(prev => ({ ...prev, status: s })), [setFilter]);
  const setViewId = useCallback((id: string | null) => setFilter(prev => ({ ...prev, viewId: id })), [setFilter]);
  const setFilters = useCallback((f: any) => setFilter(prev => ({ 
    ...prev,
    date_from: f.dateFrom !== undefined ? f.dateFrom : prev.date_from,
    date_to: f.dateTo !== undefined ? f.dateTo : prev.date_to,
      playbook_ids: f.playbookIds !== undefined ? f.playbookIds : prev.playbook_ids,
      account_ids: f.accountIds !== undefined ? f.accountIds : prev.account_ids,
    status: f.status !== undefined ? f.status : (prev as any).status,
    viewId: f.viewId !== undefined ? f.viewId : prev.viewId
  })), [setFilter]);

  const { portfolios } = usePortfolios();
  const { data: accounts } = useAccounts(portfolioId ?? undefined);
  const { data: playbooks } = usePlaybooks();
  const { data: taxonomies } = useGetTaxonomies("trades");

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
      if (cfg.date_from || cfg.date_to) count++;
      if (cfg.status) count++;
      return count;
    }
    
    if (playbookIds && playbookIds.length > 0) count++;
    if (tagIds && tagIds.length > 0) count++;
    if (accountIds && accountIds.length > 0) count++;
    if (dateFrom || dateTo) count++;
    if (status) count++;
    return count;
  }, [playbookIds, tagIds, accountIds, dateFrom, dateTo, status, activeView]);

  const filterConfig = useMemo(() => {
    const config: DashboardFilterConfig = {};
    if (dateFrom) config.date_from = dateFrom;
    if (dateTo) config.date_to = dateTo;
    if (playbookIds.length > 0) config.playbook_ids = playbookIds;
    if (accountIds.length > 0) config.account_ids = accountIds;
    if (tagIds.length > 0) config.taxonomy_ids = tagIds;
    if (status) config.status = status;
    return config;
  }, [dateFrom, dateTo, playbookIds, tagIds, accountIds, status]);

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
      if (!confirm("Delete this saved view?")) return;
      deleteViewMutation.mutate(id, {
        onSuccess: () => {
          if (viewId === id) {
            setViewId(null);
          }
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
          dateFrom: view.filter_config.date_from ?? null,
          dateTo: view.filter_config.date_to ?? null,
          playbookIds: view.filter_config.playbook_ids ?? [],
          accountIds: view.filter_config.account_ids ?? [],
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
            <button
              type="button"
              onClick={() => handleDeleteView(activeView.id)}
              disabled={deleteViewMutation.isPending}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors rounded-md disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete View
            </button>
          )}
          {/* Clear Filters (always available if there are active filters) */}
          {((playbookIds.length > 0 ||
            tagIds.length > 0 ||
            accountIds.length > 0 ||
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
        </div>
      )}

      {/* Save View Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-card border border-border p-6 shadow-2xl">
            <h2 className="mb-4 text-base font-semibold text-foreground">Save Current View</h2>
            <label className="mb-2 block text-sm font-medium text-muted-foreground">View Name</label>
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
          </div>
        </div>
      )}

      {/* Rename View Modal */}
      {showRenameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-card border border-border p-6 shadow-2xl">
            <h2 className="mb-4 text-base font-semibold text-foreground">Rename View</h2>
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
          </div>
        </div>
      )}
    </div>
  );
}
