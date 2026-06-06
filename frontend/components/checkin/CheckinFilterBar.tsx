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

import { useState, useCallback, useMemo } from "react";
import { useMarketIndexes } from "@/hooks/useCheckinDefinitions";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import {
  useSavedCheckinFilters,
  useCreateSavedCheckinFilter,
  useUpdateSavedCheckinFilter,
  useDeleteSavedCheckinFilter,
} from "@/hooks/useSavedCheckinFilters";
import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import { AnnotationFilterRows, type AnnotationFilterRow } from "@/components/ui/AnnotationFilterRows";
import { ChevronDown, ChevronRight, Save, Trash2, Edit2, RefreshCw } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Dialog from "@radix-ui/react-dialog";
import { toast } from 'react-hot-toast';

export function CheckinFilterBar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveViewName, setSaveViewName] = useState("");
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renameViewName, setRenameViewName] = useState("");
  const [selectedViewIdToRename, setSelectedViewIdToRename] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const { filter, setFilter } = useCheckinFilter();

  const { data: indices } = useMarketIndexes();
  const { data: savedViews } = useSavedCheckinFilters();
  const { data: taxonomies } = useGetTaxonomies("checkins");
  const checkinTaxonomies = (taxonomies ?? []).filter((t) => !t.is_archived);
  const { data: annotationDefs } = useGetAnnotationDefinitions("checkins");
  const checkinAnnotationDefs = (annotationDefs ?? []).filter(
    (d) => !d.is_archived && (d.scope === "checkins" || d.scope === "both")
  );

  const createViewMutation = useCreateSavedCheckinFilter();
  const updateViewMutation = useUpdateSavedCheckinFilter();
  const deleteViewMutation = useDeleteSavedCheckinFilter();

  const activeView = useMemo(() => {
    if (!filter.viewId) return null;
    return savedViews?.find((v) => v.id === filter.viewId) ?? null;
  }, [filter.viewId, savedViews]);

  const toggleTargetIndex = useCallback((id: string) => {
    setFilter((prev) => {
      const current = prev.target_indices ?? [];
      const newIndices = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
      return { ...prev, target_indices: newIndices, viewId: null };
    });
  }, [setFilter]);

  const toggleTaxonomy = useCallback((id: string) => {
    setFilter((prev) => {
      const current = prev.taxonomy_ids ?? [];
      const updated = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
      return { ...prev, taxonomy_ids: updated.length > 0 ? updated : null, viewId: null };
    });
  }, [setFilter]);

  const handleAnnotationFiltersChange = useCallback((rows: AnnotationFilterRow[]) => {
    setFilter((prev) => ({ ...prev, annotation_filters: rows, viewId: null }));
  }, [setFilter]);

  const handleSelectView = useCallback((viewId: string) => {
    const view = savedViews?.find((v) => v.id === viewId);
    if (!view) return;
    const cfg = view.filter_config as Record<string, unknown>;
    setFilter(prev => ({
      ...prev,
      viewId,
      from_date: (cfg.from_date as string | null) ?? null,
      to_date: (cfg.to_date as string | null) ?? null,
      target_indices: (cfg.target_indices as string[] | null) ?? null,
      taxonomy_ids: (cfg.taxonomy_ids as string[] | null) ?? null,
      annotation_filters: (cfg.annotation_filters as AnnotationFilterRow[] | null) ?? [],
      page: 1,
    }));
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
          target_indices: filter.target_indices,
          taxonomy_ids: filter.taxonomy_ids,
          annotation_filters: (filter.annotation_filters ?? []).map(({ _key: _, ...rest }) => rest as import("@/lib/api/types.gen").AnnotationFilterItem),
        },
      });
      setFilter((prev) => ({ ...prev, viewId: res.id }));
      setShowSaveModal(false);
      setSaveViewName("");
    } catch (e) {
      console.error("Failed to save view", e);
      toast.error("Failed to save view. Please try again.");
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
            target_indices: filter.target_indices,
            taxonomy_ids: filter.taxonomy_ids,
            annotation_filters: (filter.annotation_filters ?? []).map(({ _key: _, ...rest }) => rest as import("@/lib/api/types.gen").AnnotationFilterItem),
          },
        },
      });
    } catch (e) {
      console.error("Failed to update view", e);
      toast.error("Failed to update view. Please try again.");
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
      toast.error("Failed to rename view. Please try again.");
    }
  }, [selectedViewIdToRename, renameViewName, updateViewMutation]);

  const handleDeleteView = useCallback(async (viewId: string) => {
    try {
      await deleteViewMutation.mutateAsync(viewId);
      if (filter.viewId === viewId) {
        setFilter((prev) => ({ ...prev, viewId: null }));
      }
      setDeleteConfirmId(null);
    } catch (err) {
      console.error("Failed to delete view", err);
      toast.error("Failed to delete view. Please try again.");
    }
  }, [deleteViewMutation, filter.viewId, setFilter]);

  const handleClearFilters = useCallback(() => {
    setFilter(prev => ({
      ...prev,
      viewId: null,
      from_date: null,
      to_date: null,
      target_indices: null,
      taxonomy_ids: null,
      annotation_filters: [],
      page: 1,
    }));
  }, [setFilter]);

  // Derived counts for badge
  const activeFiltersCount = [
    filter.from_date ? 1 : 0,
    filter.to_date ? 1 : 0,
    (filter.target_indices?.length ?? 0) > 0 ? 1 : 0,
    (filter.taxonomy_ids?.length ?? 0) > 0 ? 1 : 0,
    (filter.annotation_filters?.length ?? 0) > 0 ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="w-full bg-card border border-border rounded-md shadow-sm mb-6">
      {/* Header bar with toggle */}
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            Filters
            {activeFiltersCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {activeFiltersCount}
              </span>
            )}
          </button>

          {/* Views Dropdown */}
          <div className="hidden sm:flex items-center gap-2 border-l pl-4 border-border/50">
            <span className="text-xs font-medium text-muted-foreground">Saved View</span>
            {savedViews && savedViews.length > 0 ? (
              <select
                value={filter.viewId ?? ""}
                onChange={(e) => handleSelectView(e.target.value)}
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
              onClick={handleUpdateCurrentView}
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
                setSelectedViewIdToRename(activeView.id);
                setRenameViewName(activeView.name);
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
              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-destructive/10">
                <span className="text-destructive">Are you sure?</span>
                <button
                  type="button"
                  onClick={() => handleDeleteView(activeView.id)}
                  disabled={deleteViewMutation.isPending}
                  className="px-2 py-0.5 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
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
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors rounded-md disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete View
              </button>
            )
          )}

          {activeFiltersCount > 0 && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Expanded Filter Panel */}
      {isExpanded && (
        <div className="border-t border-border/50 bg-secondary/20 p-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">

            {/* Date From */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Date From</label>
              <input
                type="date"
                value={filter.from_date || ""}
                onChange={(e) => setFilter(prev => ({ ...prev, from_date: e.target.value || null, viewId: null }))}
                className="w-full bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                title="From"
              />
            </div>

            {/* Date To */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Date To</label>
              <input
                type="date"
                value={filter.to_date || ""}
                onChange={(e) => setFilter(prev => ({ ...prev, to_date: e.target.value || null, viewId: null }))}
                className="w-full bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                title="To"
              />
            </div>

            {/* Tags */}
            {checkinTaxonomies.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Tags</label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button className="w-full flex items-center justify-between bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary text-left truncate">
                      <span className="truncate pr-2">
                        {(filter.taxonomy_ids?.length ?? 0) > 0
                          ? `${filter.taxonomy_ids!.length} selected`
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
                      {checkinTaxonomies.map((tag) => {
                        const isSelected = filter.taxonomy_ids?.includes(tag.id) ?? false;
                        return (
                          <DropdownMenu.CheckboxItem
                            key={tag.id}
                            checked={isSelected}
                            onCheckedChange={() => toggleTaxonomy(tag.id)}
                            className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                          >
                            <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                              <DropdownMenu.ItemIndicator>
                                <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-primary">
                                  <path d="M11.6666 3.5L5.24992 9.91667L2.33325 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </DropdownMenu.ItemIndicator>
                            </span>
                            <span className="text-sm font-medium text-foreground truncate" title={tag.name}>{tag.name}</span>
                          </DropdownMenu.CheckboxItem>
                        );
                      })}
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            )}

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
                        <DropdownMenu.CheckboxItem
                          key={idx.id}
                          checked={isSelected}
                          onCheckedChange={() => toggleTargetIndex(idx.id)}
                          className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                        >
                          <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                            <DropdownMenu.ItemIndicator>
                              <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-3 h-3 text-primary">
                                <path d="M11.6666 3.5L5.24992 9.91667L2.33325 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </DropdownMenu.ItemIndicator>
                          </span>
                          <span className="text-sm font-medium text-foreground truncate" title={idx.name}>{idx.name}</span>
                        </DropdownMenu.CheckboxItem>
                      );
                    })}
                    {(!indices || indices.length === 0) && (
                      <div className="text-sm text-muted-foreground px-2 py-1">No indices found</div>
                    )}
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </div>
          </div>

          {/* Annotation Filters — full width below grid */}
          {checkinAnnotationDefs.length > 0 && (
            <div className="pt-3 border-t border-border/50">
              <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Annotation Filters</label>
              <AnnotationFilterRows
                rows={filter.annotation_filters ?? []}
                definitions={checkinAnnotationDefs}
                onChange={handleAnnotationFiltersChange}
              />
            </div>
          )}
        </div>
      )}

      {/* Save View Modal */}
      <Dialog.Root open={showSaveModal} onOpenChange={(open) => {
        setShowSaveModal(open);
        if (!open) setSaveViewName("");
      }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-xl bg-card border border-border p-6 shadow-2xl">
            <Dialog.Title className="mb-4 text-base font-semibold text-foreground">Save Current View</Dialog.Title>
            <label className="mb-2 block text-sm font-medium text-muted-foreground">View Name</label>
            <input
              type="text"
              className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="View name..."
              value={saveViewName}
              onChange={(e) => setSaveViewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleSaveView()}
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
                onClick={() => void handleSaveView()}
                className="btn-primary disabled:opacity-50"
              >
                {createViewMutation.isPending ? "Saving…" : "Save View"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Rename View Modal */}
      <Dialog.Root open={showRenameModal} onOpenChange={(open) => { setShowRenameModal(open); if (!open) { setSelectedViewIdToRename(null); setRenameViewName(""); } }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-[50%] top-[50%] z-50 w-full max-w-md translate-x-[-50%] translate-y-[-50%] rounded-xl bg-card border border-border p-6 shadow-2xl">
            <Dialog.Title className="mb-4 text-base font-semibold text-foreground">Rename View</Dialog.Title>
            <label className="mb-2 block text-sm font-medium text-muted-foreground">New Name</label>
            <input
              type="text"
              className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="View name..."
              value={renameViewName}
              onChange={(e) => setRenameViewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void handleRenameView()}
              autoFocus
            />
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRenameModal(false);
                  setSelectedViewIdToRename(null);
                }}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!renameViewName.trim() || updateViewMutation.isPending}
                onClick={() => void handleRenameView()}
                className="btn-primary disabled:opacity-50"
              >
                {updateViewMutation.isPending ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
