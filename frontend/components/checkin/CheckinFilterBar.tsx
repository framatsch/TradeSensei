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

"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useMarketIndexes } from "@/hooks/useCheckinDefinitions";
import {
  useSavedCheckinFilters,
  useCreateSavedCheckinFilter,
  useUpdateSavedCheckinFilter,
  useDeleteSavedCheckinFilter,
} from "@/hooks/useSavedCheckinFilters";
import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import { ChevronDown, ChevronRight, Save, Trash2, Edit2, RefreshCw, Filter as FilterIcon } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";

export function CheckinFilterBar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveViewName, setSaveViewName] = useState("");
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renameViewName, setRenameViewName] = useState("");
  const [selectedViewIdToRename, setSelectedViewIdToRename] = useState<string | null>(null);

  const { filter, setFilter } = useCheckinFilter();

  const { data: indices } = useMarketIndexes();
  const { data: savedViews } = useSavedCheckinFilters();

  const createViewMutation = useCreateSavedCheckinFilter();
  const updateViewMutation = useUpdateSavedCheckinFilter();
  const deleteViewMutation = useDeleteSavedCheckinFilter();

  const activeViewName = useMemo(() => {
    if (!filter.viewId) return null;
    return savedViews?.find((v) => v.id === filter.viewId)?.name ?? null;
  }, [filter.viewId, savedViews]);

  // Click outside to close expanded bar
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (isExpanded && containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsExpanded(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isExpanded]);

  const toggleTargetIndex = useCallback((id: string) => {
    setFilter((prev) => {
      const current = prev.target_indices ?? [];
      const newIndices = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
      return { ...prev, target_indices: newIndices, viewId: null };
    });
  }, [setFilter]);

  const handleSelectView = useCallback((viewId: string) => {
    const view = savedViews?.find((v) => v.id === viewId);
    if (!view) return;
    setFilter({
      viewId,
      from_date: view.filter_config.from_date ?? null,
      to_date: view.filter_config.to_date ?? null,
      regime: view.filter_config.regime ?? null,
      target_indices: view.filter_config.target_indices ?? null,
      has_media: view.filter_config.has_media ?? null,
    });
    setIsExpanded(false);
  }, [savedViews, setFilter]);

  const handleSaveView = useCallback(async () => {
    if (!saveViewName.trim()) return;
    try {
      const res = await createViewMutation.mutateAsync({
        name: saveViewName.trim(),
        is_default: false,
        filter_config: {
          from_date: filter.from_date,
          to_date: filter.to_date,
          regime: filter.regime,
          target_indices: filter.target_indices,
          has_media: filter.has_media,
        },
      });
      setFilter((prev) => ({ ...prev, viewId: res.id }));
      setShowSaveModal(false);
      setSaveViewName("");
    } catch (e) {
      console.error("Failed to save view", e);
    }
  }, [saveViewName, filter, createViewMutation, setFilter]);

  const handleUpdateCurrentView = useCallback(async () => {
    if (!filter.viewId) return;
    try {
      await updateViewMutation.mutateAsync({
        id: filter.viewId,
        payload: {
          filter_config: {
            from_date: filter.from_date,
            to_date: filter.to_date,
            regime: filter.regime,
            target_indices: filter.target_indices,
            has_media: filter.has_media,
          },
        },
      });
    } catch (e) {
      console.error("Failed to update view", e);
    }
  }, [filter, updateViewMutation]);

  const handleRenameView = useCallback(async () => {
    if (!selectedViewIdToRename || !renameViewName.trim()) return;
    try {
      await updateViewMutation.mutateAsync({
        id: selectedViewIdToRename,
        payload: { name: renameViewName.trim() },
      });
      setShowRenameModal(false);
      setSelectedViewIdToRename(null);
    } catch (e) {
      console.error("Failed to rename view", e);
    }
  }, [selectedViewIdToRename, renameViewName, updateViewMutation]);

  const handleDeleteView = useCallback(async (e: React.MouseEvent, viewId: string) => {
    e.stopPropagation();
    try {
      await deleteViewMutation.mutateAsync(viewId);
      if (filter.viewId === viewId) {
        setFilter((prev) => ({ ...prev, viewId: null }));
      }
    } catch (err) {
      console.error("Failed to delete view", err);
    }
  }, [deleteViewMutation, filter.viewId, setFilter]);

  const handleClearFilters = useCallback(() => {
    setFilter({
      viewId: null,
      from_date: null,
      to_date: null,
      regime: null,
      target_indices: null,
      has_media: null,
    });
  }, [setFilter]);

  // Derived counts for badge
  const activeFiltersCount = [
    filter.from_date || filter.to_date ? 1 : 0,
    filter.regime ? 1 : 0,
    (filter.target_indices?.length ?? 0) > 0 ? 1 : 0,
    filter.has_media !== null && filter.has_media !== undefined ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  return (
    <div ref={containerRef} className="relative z-30 mb-6 bg-card border-b border-border">
      {/* Top Row: Current Selection & Toggle */}
      <div className="flex flex-wrap items-center justify-between px-4 sm:px-6 lg:px-8 py-3 gap-y-3">
        <div className="flex items-center gap-3">
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-foreground bg-secondary hover:bg-secondary/80 rounded-md transition-colors">
                <FilterIcon size={14} />
                <span>{activeViewName ?? "Custom View"}</span>
                <ChevronDown size={14} className="text-muted-foreground" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="min-w-[200px] rounded-lg bg-card border border-border shadow-lg p-1 z-50 animate-in fade-in-80 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-100 data-[state=closed]:zoom-out-95"
                sideOffset={4}
                align="start"
              >
                <DropdownMenu.Group>
                  <DropdownMenu.Label className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Saved Views</DropdownMenu.Label>
                  {savedViews?.map((v) => (
                    <DropdownMenu.Item
                      key={v.id}
                      className="group relative flex items-center justify-between rounded-md px-2 py-1.5 text-sm font-medium text-foreground hover:bg-secondary cursor-pointer"
                      onClick={() => handleSelectView(v.id)}
                    >
                      <span className="truncate pr-4">{v.name}</span>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          className="p-1 hover:bg-muted rounded text-muted-foreground"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedViewIdToRename(v.id);
                            setRenameViewName(v.name);
                            setShowRenameModal(true);
                          }}
                          title="Rename"
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          className="p-1 hover:bg-red-500/20 hover:text-red-500 rounded text-muted-foreground"
                          onClick={(e) => handleDeleteView(e, v.id)}
                          title="Delete"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </DropdownMenu.Item>
                  ))}
                  {(!savedViews || savedViews.length === 0) && (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground italic">No saved views</div>
                  )}
                </DropdownMenu.Group>
                <DropdownMenu.Separator className="h-px bg-border my-1" />
                <DropdownMenu.Item
                  className="rounded-md px-2 py-1.5 text-sm font-medium text-foreground hover:bg-secondary cursor-pointer flex items-center gap-2"
                  onClick={handleClearFilters}
                >
                  <RefreshCw size={14} className="text-muted-foreground" />
                  Clear Filters
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>

          {activeFiltersCount > 0 && (
            <span className="inline-flex items-center justify-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {activeFiltersCount} active
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {filter.viewId && (
            <button
              onClick={handleUpdateCurrentView}
              disabled={updateViewMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
              title="Save changes to this view"
            >
              <RefreshCw size={14} className={updateViewMutation.isPending ? "animate-spin" : ""} />
              Update View
            </button>
          )}
          <button
            onClick={() => {
              setSaveViewName("");
              setShowSaveModal(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <Save size={14} />
            Save As
          </button>
          <div className="h-4 w-px bg-border mx-1" />
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {isExpanded ? "Hide Filters" : "Show Filters"}
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        </div>
      </div>

      {/* Expanded Filter Panel */}
      {isExpanded && (
        <div className="border-t border-border bg-secondary/30 p-4 sm:px-6 lg:px-8 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            
            {/* Date Range */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Date Range</label>
              <div className="flex flex-col gap-2">
                <input
                  type="date"
                  value={filter.from_date || ""}
                  onChange={(e) => setFilter(prev => ({ ...prev, from_date: e.target.value || null, viewId: null }))}
                  className="w-full bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  title="From"
                />
                <input
                  type="date"
                  value={filter.to_date || ""}
                  onChange={(e) => setFilter(prev => ({ ...prev, to_date: e.target.value || null, viewId: null }))}
                  className="w-full bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                  title="To"
                />
              </div>
            </div>

            {/* Regime */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Market Phase</label>
              <select
                value={filter.regime || ""}
                onChange={(e) => setFilter(prev => ({ ...prev, regime: e.target.value || null, viewId: null }))}
                className="w-full bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Phases</option>
                <option value="BULL">Bull</option>
                <option value="BEAR">Bear</option>
                <option value="CHOP">Chop</option>
              </select>
            </div>

            {/* Target Indices */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Target Indices</label>
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button className="w-full flex items-center justify-between bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary text-left truncate">
                    <span className="truncate pr-2">
                      {filter.target_indices?.length
                        ? `${filter.target_indices.length} selected`
                        : "Any"}
                    </span>
                    <ChevronDown size={14} className="text-muted-foreground shrink-0" />
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    className="w-56 rounded-lg bg-card border border-border shadow-lg p-2 z-50 max-h-60 overflow-y-auto"
                    sideOffset={4}
                    align="start"
                  >
                    {indices?.map((idx) => {
                      const isSelected = filter.target_indices?.includes(idx.id) ?? false;
                      return (
                        <div
                          key={idx.id}
                          className="flex items-center gap-2 px-2 py-1.5 hover:bg-secondary rounded cursor-pointer group"
                          onClick={() => toggleTargetIndex(idx.id)}
                        >
                          <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors ${isSelected ? 'bg-primary border-primary' : 'border-muted-foreground/50 group-hover:border-foreground'}`}>
                            {isSelected && <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-primary-foreground"><path d="M11.6666 3.5L5.24992 9.91667L2.33325 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
                          </div>
                          <span className="text-sm font-medium text-foreground truncate" title={idx.name}>{idx.name}</span>
                        </div>
                      );
                    })}
                    {(!indices || indices.length === 0) && (
                      <div className="text-sm text-muted-foreground px-2 py-1">No indices found</div>
                    )}
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </div>

            {/* Media */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Has Media</label>
              <div className="flex rounded-md border border-border overflow-hidden">
                <button
                  onClick={() => setFilter(prev => ({ ...prev, has_media: null, viewId: null }))}
                  className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${filter.has_media === null ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
                >
                  Any
                </button>
                <div className="w-px bg-border" />
                <button
                  onClick={() => setFilter(prev => ({ ...prev, has_media: true, viewId: null }))}
                  className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${filter.has_media === true ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
                >
                  Yes
                </button>
                <div className="w-px bg-border" />
                <button
                  onClick={() => setFilter(prev => ({ ...prev, has_media: false, viewId: null }))}
                  className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${filter.has_media === false ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground"}`}
                >
                  No
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
                disabled={!saveViewName.trim() || createViewMutation.isPending}
                onClick={handleSaveView}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
              >
                {createViewMutation.isPending ? "Saving…" : "Save View"}
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
            <label className="mb-2 block text-sm font-medium text-muted-foreground">New Name</label>
            <input
              type="text"
              className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="View name..."
              value={renameViewName}
              onChange={(e) => setRenameViewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRenameView()}
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRenameModal(false);
                  setSelectedViewIdToRename(null);
                  setRenameViewName("");
                }}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!renameViewName.trim() || updateViewMutation.isPending}
                onClick={handleRenameView}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
              >
                {updateViewMutation.isPending ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
