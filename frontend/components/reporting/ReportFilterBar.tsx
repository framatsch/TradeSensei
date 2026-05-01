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
import { useTags } from "@/hooks/useTags";
import { useSavedViews, useSaveView, useDeleteView } from "@/hooks/useReportingViews";
import { useReportingFilterStore } from "@/stores/reportingFilterStore";
import { ChevronDown, ChevronRight, X, Save, Trash2 } from "lucide-react";
import type { Playbook, Tag } from "@/lib/types";
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
  const { data: tags } = useTags();

  // ── Saved views logic ────────────────────────────────────────────────────
  const { data: savedViews } = useSavedViews(portfolioId);
  const saveViewMutation = useSaveView(portfolioId);
  const deleteViewMutation = useDeleteView(portfolioId);

  const [saveViewName, setSaveViewName] = useState("");
  const [showSaveInput, setShowSaveInput] = useState(false);

  const filterConfig = useMemo(() => {
    const config: DashboardFilterConfig = {};
    if (dateFrom) config.date_from = dateFrom;
    if (dateTo) config.date_to = dateTo;
    if (playbookIds.length > 0) config.playbook_ids = playbookIds;
    if (tagIds.length > 0) config.tag_ids = tagIds;
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
          setShowSaveInput(false);
        },
      },
    );
  }, [saveViewName, portfolioId, filterConfig, saveViewMutation, setViewId]);

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
          tagIds: view.filter_config.tag_ids ?? [],
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
            Filter Configuration
            {((playbookIds.length > 0 ? 1 : 0) +
              (tagIds.length > 0 ? 1 : 0) +
              (dateFrom || dateTo ? 1 : 0) +
              (includeOpenTrades ? 1 : 0)) > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {(playbookIds.length > 0 ? 1 : 0) +
                  (tagIds.length > 0 ? 1 : 0) +
                  (dateFrom || dateTo ? 1 : 0) +
                  (includeOpenTrades ? 1 : 0)}
              </span>
            )}
          </button>

          {/* Saved View Select in Header */}
          <div className="hidden sm:flex items-center gap-2 border-l pl-4 border-border/50">
            <span className="text-xs text-muted-foreground font-medium">View:</span>
            <select
              value={viewId ?? ""}
              onChange={(e) => {
                if (e.target.value) {
                  handleViewSelect(e.target.value);
                } else {
                  setViewId(null);
                }
              }}
              className="px-2 py-1 bg-transparent border-none text-foreground text-sm font-medium focus:outline-none focus:ring-0 cursor-pointer"
            >
              <option value="">Unsaved view</option>
              {(savedViews ?? []).map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Save Controls in Header */}
        <div className="flex items-center gap-2">
          {showSaveInput ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={saveViewName}
                onChange={(e) => setSaveViewName(e.target.value)}
                placeholder="View name..."
                className="w-32 sm:w-40 px-2 py-1 bg-secondary border border-border rounded-md text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveView();
                  if (e.key === "Escape") {
                    setShowSaveInput(false);
                    setSaveViewName("");
                  }
                }}
                autoFocus
              />
              <button
                type="button"
                onClick={handleSaveView}
                disabled={!saveViewName.trim() || saveViewMutation.isPending}
                className="px-2 py-1 text-xs rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {saveViewMutation.isPending ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSaveInput(false);
                  setSaveViewName("");
                }}
                className="px-2 py-1 text-xs rounded-md bg-secondary text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setShowSaveInput(true)}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors px-3 py-1.5 bg-primary/10 rounded-md"
              >
                <Save className="w-3.5 h-3.5" />
                Save View
              </button>
              {viewId && (
                <button
                  type="button"
                  onClick={() => handleDeleteView(viewId)}
                  disabled={deleteViewMutation.isPending}
                  className="flex items-center gap-1.5 text-xs font-medium text-danger hover:text-danger/80 transition-colors px-3 py-1.5 bg-destructive/10 rounded-md disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete
                </button>
              )}
            </>
          )}

          {/* Clear Filters (always available if there are active filters) */}
          {((playbookIds.length > 0 ||
            tagIds.length > 0 ||
            dateFrom ||
            dateTo ||
            includeOpenTrades) ? 1 : 0) > 0 && (
            <button
              type="button"
              onClick={() => {
                setDateFrom(null);
                setDateTo(null);
                setPlaybookIds([]);
                setTagIds([]);
                setIncludeOpenTrades(false);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors rounded-md ml-2 border-l border-border/50 pl-4"
            >
              <X className="w-3.5 h-3.5" />
              Clear Filters
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
                onChange={(e) => setDateFrom(e.target.value || null)}
                className={INPUT_CLASS}
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

            {/* Tag multi-select */}
            <MultiSelect
              label="Tags"
              items={(tags ?? []).map((t: Tag) => ({
                id: t.id,
                name: t.name,
              }))}
              selectedIds={tagIds}
              onChange={setTagIds}
              placeholder="All tags"
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
    </div>
  );
}