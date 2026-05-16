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

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { usePortfolios } from "@/hooks/usePortfolios";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useSavedViews, useSaveView, useUpdateView, useDeleteView } from "@/hooks/useReportingViews";
import { useReportingFilterStore } from "@/stores/reportingFilterStore";
import { ChevronDown, ChevronRight, X, Save, Trash2, Edit2, RefreshCw, Filter as FilterIcon, Lock } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import type { Playbook } from "@/lib/types";
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

export function ReportFilterBar() {
  const [collapsed, setCollapsed] = useState(false);

  const {
    portfolioId,
    dateFrom,
    dateTo,
    playbookIds,
    tagIds,
    includeOpenTrades,
    viewId,
    setPortfolioId,
    setDateFrom,
    setDateTo,
    setPlaybookIds,
    setTagIds,
    setIncludeOpenTrades,
    setViewId,
    setFilters,
  } = useReportingFilterStore();

  const { portfolios } = usePortfolios();
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

  const handleSetIncludeOpenTrades = useCallback((val: boolean) => {
    if (viewId) setViewId(null);
    setIncludeOpenTrades(val);
  }, [viewId, setViewId, setIncludeOpenTrades]);

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
      if (cfg.date_from || cfg.date_to) count++;
      // backend doesn't have an includeOpenTrades concept currently in DashboardFilterConfig natively,
      // but we'll just check if it existed:
      // (For now, we count 1 for each active filter block)
      return count;
    }
    
    if (playbookIds && playbookIds.length > 0) count++;
    if (tagIds && tagIds.length > 0) count++;
    if (dateFrom || dateTo) count++;
    if (includeOpenTrades) count++;
    return count;
  }, [playbookIds, tagIds, dateFrom, dateTo, includeOpenTrades, activeView]);

  const filterConfig = useMemo(() => {
    const config: DashboardFilterConfig = {};
    if (dateFrom) config.date_from = dateFrom;
    if (dateTo) config.date_to = dateTo;
    if (playbookIds.length > 0) config.playbook_ids = playbookIds;
    return config;
  }, [dateFrom, dateTo, playbookIds, tagIds]);

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
        });
      }
    },
    [savedViews, setViewId, setFilters],
  );

  const handlePortfolioChange = useCallback(
    (id: string) => {
      setPortfolioId(id);
    },
    [setPortfolioId],
  );

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
            dateFrom ||
            dateTo ||
            includeOpenTrades) ? 1 : 0) > 0 && (
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
                onClick={() => {
                  handleSetDateFrom(null);
                  handleSetDateTo(null);
                  handleSetPlaybookIds([]);
                  handleSetTagIds([]);
                  handleSetIncludeOpenTrades(false);
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {/* Portfolio selector */}
            <div>
              <label className={LABEL_CLASS}>Portfolio</label>
              <select
                value={portfolioId ?? ""}
                onChange={(e) => handlePortfolioChange(e.target.value)}
                className={INPUT_CLASS}
              >
                <option value="" disabled>
                  Select portfolio...
                </option>
                {portfolios.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

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

            {/* Open trades toggle */}
            <div className="flex items-center gap-2 h-[38px] mt-6">
              <input
                type="checkbox"
                id="includeOpen"
                checked={includeOpenTrades}
                onChange={(e) => handleSetIncludeOpenTrades(e.target.checked)}
                className="w-4 h-4 rounded border-border accent-primary"
              />
            </div>

            {/* Date to */}
            <div>
              <label className={LABEL_CLASS}>Date To</label>
              <input
                type="date"
                value={dateTo ?? ""}
                onChange={(e) => setDateTo(e.target.value || null)}
                className={INPUT_CLASS}
              />
            </div>

            {/* Playbook multi-select */}
            <MultiSelect
              label="Playbooks"
              items={(playbooks ?? []).map((pb: Playbook) => ({
                id: pb.id,
                name: pb.name,
              }))}
              selectedIds={playbookIds}
              onChange={setPlaybookIds}
              placeholder="All playbooks"
            />

            {/* Taxonomy multi-select */}
            <MultiSelect
              label="Taxonomies"
              items={(taxonomies ?? []).map((t) => ({
                id: t.id,
                name: t.name,
              }))}
              selectedIds={tagIds}
              onChange={setTagIds}
              placeholder="All taxonomies"
            />

            {/* Trade status toggle */}
            <div>
              <label className={LABEL_CLASS}>Trade Status</label>
              <div className="flex items-center gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setIncludeOpenTrades(false)}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    !includeOpenTrades
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Closed Only
                </button>
                <button
                  type="button"
                  onClick={() => setIncludeOpenTrades(true)}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    includeOpenTrades
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Include Open
                </button>
              </div>
            </div>
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
              placeholder="e.g. Q1 Performance"
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
