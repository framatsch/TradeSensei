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

import { scopeLabel } from '@/lib/utils/scopeLabel';
import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, ArchiveRestore, Loader2, AlertCircle, ChevronDown, Check, ArrowLeft, Edit3 } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { toast } from "react-hot-toast";
import {
  useGetTaxonomies,
  useCreateTaxonomy,
  useUpdateTaxonomy,
  useDeleteTaxonomy,
  useArchiveTaxonomy,
  useUnarchiveTaxonomy,
  fetchTaxonomyAssignmentCount,
} from "@/hooks/useTaxonomies";
import { THEME_COLORS } from "@/lib/constants/colors";
import type { TaxonomyResponse, TaxonomyCreate } from "@/lib/api/types.gen";

import { DynamicIcon } from "@/components/ui/DynamicIcon";

function getDisplayScope(scopeStr: string): string {
  return scopeLabel(scopeStr);
}

export function TaxonomyManager() {
  const [showArchived, setShowArchived] = useState(false);
  const { data: taxonomies, isLoading, error } = useGetTaxonomies(undefined, showArchived);
  const createMutation = useCreateTaxonomy();
  const updateMutation = useUpdateTaxonomy();
  const deleteMutation = useDeleteTaxonomy();
  const archiveMutation = useArchiveTaxonomy();
  const unarchiveMutation = useUnarchiveTaxonomy();

  const [isViewing, setIsViewing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedTaxonomy, setSelectedTaxonomy] = useState<TaxonomyResponse | null>(null);
  
  // Inline delete confirmation: holds the id of the taxonomy pending deletion
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  
  // Danger Zone states
  const [assignmentCounts, setAssignmentCounts] = useState<{
    trade_count: number;
    checkin_count: number;
    playbook_count: number;
    total_count: number;
  } | null>(null);
  const [isFetchingCounts, setIsFetchingCounts] = useState(false);
  const [confirmNameInput, setConfirmNameInput] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["trades"]);
  const [colorHex, setColorHex] = useState("#3b82f6");
  const [description, setDescription] = useState("");
  const [iconIdentifier, setIconIdentifier] = useState("");

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
        Error loading taxonomies.
      </div>
    );
  }

  const handleView = (taxonomy: TaxonomyResponse) => {
    setSelectedTaxonomy(taxonomy);
    setIsViewing(true);
    setIsEditing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCloseDetails = () => {
    setIsViewing(false);
    setSelectedTaxonomy(null);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleEdit = (taxonomy: TaxonomyResponse) => {
    setSelectedTaxonomy(taxonomy);
    setName(taxonomy.name);
    
    // Parse taxonomy.scope to set initial scopes array (comma-separated post-migration).
    const parsedScopes: string[] = taxonomy.scope
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    setSelectedScopes(parsedScopes);
    setColorHex(taxonomy.color_hex);
    setDescription(taxonomy.description || "");
    setIconIdentifier(taxonomy.icon_identifier || "");
    setIsEditing(true);
    setIsViewing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCreate = () => {
    setSelectedTaxonomy(null);
    setName("");
    setSelectedScopes(["trades"]);
    setColorHex("#3b82f6");
    setDescription("");
    setIconIdentifier("");
    setIsEditing(true);
    setIsViewing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCancel = () => {
    setIsEditing(false);
    if (selectedTaxonomy) {
      // Return to viewing details if we were editing from detail view
      setIsViewing(true);
    } else {
      setSelectedTaxonomy(null);
    }
  };

  const handleScopeToggle = (scopeValue: string) => {
    if (selectedScopes.includes(scopeValue)) {
      if (selectedScopes.length <= 1) {
        toast.error("At least one scope must be selected.");
        return;
      }
      setSelectedScopes(selectedScopes.filter((s) => s !== scopeValue));
    } else {
      setSelectedScopes([...selectedScopes, scopeValue]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    if (selectedScopes.length === 0) {
      toast.error("Please select at least one scope.");
      return;
    }

    const scopePayload = [...selectedScopes].sort().join(",");

    try {
      if (selectedTaxonomy && isEditing) {
        await updateMutation.mutateAsync({
          taxonomyId: selectedTaxonomy.id,
          payload: {
            name: name.trim(),
            scope: scopePayload,
            color_hex: colorHex,
            description: description.trim() || null,
            icon_identifier: iconIdentifier.trim() || null,
          }
        });
        
        // Update local detail view data
        const updatedTaxonomy: TaxonomyResponse = {
          ...selectedTaxonomy,
          name: name.trim(),
          scope: scopePayload,
          color_hex: colorHex,
          description: description.trim() || null,
          icon_identifier: iconIdentifier.trim() || null,
        };
        setSelectedTaxonomy(updatedTaxonomy);
      } else {
        const payload: TaxonomyCreate = {
          name: name.trim(),
          scope: scopePayload,
          color_hex: colorHex,
        };
        if (description.trim()) {
          payload.description = description.trim();
        }
        if (iconIdentifier.trim()) {
          payload.icon_identifier = iconIdentifier.trim();
        }
        await createMutation.mutateAsync(payload);
      }
      setIsEditing(false);
      setIsViewing(selectedTaxonomy !== null);
    } catch (err: any) {
      console.error(err);
      const errMsg = err?.response?.data?.detail || err?.message || "Failed to save tag. Please try again.";
      toast.error(errMsg);
    }
  };

  const handleArchiveToggle = async (taxonomy: TaxonomyResponse) => {
    try {
      if (taxonomy.is_archived) {
        const updated = await unarchiveMutation.mutateAsync({ taxonomyId: taxonomy.id });
        setSelectedTaxonomy(updated);
      } else {
        const updated = await archiveMutation.mutateAsync({ taxonomyId: taxonomy.id });
        setSelectedTaxonomy(updated);
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || "Failed to update archive status.";
      toast.error(errMsg);
    }
  };

  const handleDeleteClick = async (taxonomy: TaxonomyResponse) => {
    setConfirmDeleteId(taxonomy.id);
    setConfirmNameInput("");
    setIsFetchingCounts(true);
    try {
      const counts = await fetchTaxonomyAssignmentCount(taxonomy.id);
      setAssignmentCounts(counts);
    } catch (err) {
      console.error("Failed to fetch taxonomy assignment counts:", err);
      // Fallback
      setAssignmentCounts({ trade_count: 0, checkin_count: 0, playbook_count: 0, total_count: 0 });
    } finally {
      setIsFetchingCounts(false);
    }
  };

  const handleDeleteConfirm = async (taxonomy: TaxonomyResponse) => {
    try {
      const hasAssignments = assignmentCounts && assignmentCounts.total_count > 0;
      await deleteMutation.mutateAsync({
        taxonomyId: taxonomy.id,
        force: hasAssignments ? true : false,
      });
      setConfirmDeleteId(null);
      setAssignmentCounts(null);
      setConfirmNameInput("");
      if (selectedTaxonomy?.id === taxonomy.id) {
        handleCloseDetails();
      }
    } catch (err: any) {
      console.error(err);
      setConfirmDeleteId(null);
      setAssignmentCounts(null);
      setConfirmNameInput("");
      const errMsg = err?.response?.data?.detail || "Could not delete tag.";
      toast.error(errMsg);
    }
  };

  return (
    <div className="space-y-6">
      {!isEditing && !isViewing && (
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div
              role="switch"
              aria-checked={showArchived}
              tabIndex={0}
              onClick={() => setShowArchived((v) => !v)}
              onKeyDown={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); setShowArchived((v) => !v); } }}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                showArchived ? "bg-primary" : "bg-secondary border border-border"
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-primary-foreground shadow transition-transform ${
                  showArchived ? "translate-x-4" : "translate-x-1"
                }`}
              />
            </div>
            <span className="text-sm text-muted-foreground">Show Archived</span>
          </label>
          <button
            onClick={handleCreate}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            New Tag
          </button>
        </div>
      )}

      {isViewing && selectedTaxonomy && !isEditing ? (
        /* Read-Only Details View modeled after Playbooks */
        <div className="solid-card p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={handleCloseDetails}
                className="p-1.5 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                aria-label="Back to list"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div
                className="w-5 h-5 rounded-full flex-shrink-0"
                style={{ backgroundColor: selectedTaxonomy.color_hex }}
              />
              {selectedTaxonomy.icon_identifier && (
                <DynamicIcon name={selectedTaxonomy.icon_identifier} className="w-5 h-5 text-muted-foreground" />
              )}
              <h3 className="text-xl font-semibold text-foreground">{selectedTaxonomy.name}</h3>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleEdit(selectedTaxonomy)}
                className="btn-primary shrink-0"
              >
                <Edit3 className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={() => void handleArchiveToggle(selectedTaxonomy)}
                disabled={archiveMutation.isPending || unarchiveMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary border border-border rounded-lg transition-colors disabled:opacity-50"
              >
                {selectedTaxonomy.is_archived ? (
                  <>
                    <ArchiveRestore className="w-3.5 h-3.5" />
                    Unarchive
                  </>
                ) : (
                  <>
                    <Archive className="w-3.5 h-3.5" />
                    Archive
                  </>
                )}
              </button>
              <button
                onClick={() => void handleDeleteClick(selectedTaxonomy)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:text-destructive-foreground hover:bg-destructive border border-destructive/30 rounded-lg transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          </div>

          {/* Delete area inside details view */}
          {confirmDeleteId === selectedTaxonomy.id && (
            <div className="border-t border-b border-border py-4">
              {isFetchingCounts ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing tag usage...
                </div>
              ) : assignmentCounts && assignmentCounts.total_count > 0 ? (
                /* RED DANGER ZONE for active assignments */
                <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30 space-y-3">
                  <div className="flex items-start gap-2.5 text-sm">
                    <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
                    <div className="text-foreground flex-1 space-y-1">
                      <p className="font-semibold text-destructive uppercase tracking-wide text-xs">
                        Danger Zone: Tag is in use!
                      </p>
                      <p className="text-sm">
                        This tag is currently assigned to:
                      </p>
                      <ul className="list-disc pl-5 text-xs space-y-0.5 font-medium">
                        {assignmentCounts.trade_count > 0 && (
                          <li>{assignmentCounts.trade_count} trade(s)</li>
                        )}
                        {assignmentCounts.checkin_count > 0 && (
                          <li>{assignmentCounts.checkin_count} check-in(s)</li>
                        )}
                        {assignmentCounts.playbook_count > 0 && (
                          <li>{assignmentCounts.playbook_count} playbook(s)</li>
                        )}
                      </ul>
                      <p className="text-xs text-muted-foreground pt-1">
                        Deleting this tag will <strong>permanently remove all of these assignments</strong> from your trades/check-ins/playbooks! This action cannot be undone.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-1 border-t border-destructive/20">
                    <label className="block text-xs font-medium text-muted-foreground">
                      Type the name of the tag <span className="font-bold text-foreground select-all">&ldquo;{selectedTaxonomy.name}&rdquo;</span> to confirm:
                    </label>
                    <input
                      type="text"
                      value={confirmNameInput}
                      onChange={(e) => setConfirmNameInput(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-destructive/30 rounded-md text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-destructive placeholder-muted-foreground/30"
                      placeholder="Tag name"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-1">
                    <button
                      onClick={() => {
                        setConfirmDeleteId(null);
                        setAssignmentCounts(null);
                        setConfirmNameInput("");
                      }}
                      className="px-3 py-1 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 text-xs font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => void handleDeleteConfirm(selectedTaxonomy)}
                      disabled={deleteMutation.isPending || confirmNameInput !== selectedTaxonomy.name}
                      className="px-3 py-1 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-xs font-medium disabled:cursor-not-allowed"
                    >
                      {deleteMutation.isPending ? "Wiping..." : "Permanently Delete & Wipe Assignments"}
                    </button>
                  </div>
                </div>
              ) : (
                /* Simple confirm box for 0 assignments */
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm">
                  <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
                  <span className="text-foreground flex-1">
                    Are you sure you want to delete tag &ldquo;{selectedTaxonomy.name}&rdquo;?
                  </span>
                  <button
                    onClick={() => void handleDeleteConfirm(selectedTaxonomy)}
                    disabled={deleteMutation.isPending}
                    className="px-3 py-1 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-xs font-medium"
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Delete"}
                  </button>
                  <button
                    onClick={() => {
                      setConfirmDeleteId(null);
                      setAssignmentCounts(null);
                    }}
                    className="px-3 py-1 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 text-xs font-medium"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="space-y-4">
            {/* Row 1: Status & Scope */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Status
                </h4>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${
                    selectedTaxonomy.is_archived
                      ? "surface-warning text-warning"
                      : "surface-success text-success"
                  }`}
                >
                  {selectedTaxonomy.is_archived ? "Archived" : "Active"}
                </span>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Scopes
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedTaxonomy.scope.split(",").map((s) => (
                    <span
                      key={s}
                      className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-foreground border border-border uppercase"
                    >
                      {s.trim() === "checkins" ? "Check-ins" : s.trim()}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Row 2: Description presented as a clean 1-line text container box */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Description
              </h4>
              <div className="w-full bg-secondary/20 px-3 py-2 border border-border/50 rounded-lg text-sm text-muted-foreground truncate">
                {selectedTaxonomy.description || (
                  <span className="italic text-muted-foreground/30">No description provided.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : isEditing ? (
        <div className="solid-card p-4">
          <h3 className="text-lg font-medium mb-4">
            {selectedTaxonomy ? "Edit Tag" : "Create Tag"}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  aria-label="Tag name"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-muted-foreground/50 disabled:opacity-50"
                  placeholder="e.g. FOMO, High Conviction"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button 
                      type="button"
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    >
                      <span className="truncate pr-2">
                        {getDisplayScope(selectedScopes.join(",")) || "Select scope..."}
                      </span>
                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content className="w-56 rounded-lg bg-card border border-border shadow-lg p-2 z-50">
                      <DropdownMenu.CheckboxItem
                        checked={selectedScopes.includes("trades")}
                        onCheckedChange={() => handleScopeToggle("trades")}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Trades</span>
                      </DropdownMenu.CheckboxItem>

                      <DropdownMenu.CheckboxItem
                        checked={selectedScopes.includes("checkins")}
                        onCheckedChange={() => handleScopeToggle("checkins")}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Check-ins</span>
                      </DropdownMenu.CheckboxItem>

                      <DropdownMenu.Separator className="h-px bg-border my-1" />

                      <DropdownMenu.CheckboxItem
                        checked={selectedScopes.includes("playbook")}
                        onCheckedChange={() => handleScopeToggle("playbook")}
                        className="relative flex items-center px-2 py-1.5 pl-8 hover:bg-secondary focus:bg-secondary rounded cursor-pointer outline-none"
                      >
                        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
                          <DropdownMenu.ItemIndicator>
                            <Check className="w-3 h-3 text-primary" />
                          </DropdownMenu.ItemIndicator>
                        </span>
                        <span className="text-sm font-medium text-foreground">Playbook</span>
                      </DropdownMenu.CheckboxItem>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Icon
                </label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button 
                      type="button"
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <DynamicIcon name={iconIdentifier || "tag"} className="w-4 h-4 text-muted-foreground shrink-0" />
                        <span className="truncate">{iconIdentifier || "Select icon..."}</span>
                      </div>
                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content className="w-64 rounded-lg bg-card border border-border shadow-lg p-2 z-50 max-h-60 overflow-y-auto">
                      <div className="grid grid-cols-4 gap-2">
                        {["tag", "trending-up", "trending-down", "alert-circle", "check-circle", "book-open", "zap", "target", "shield", "bar-chart-2", "activity", "clock", "calendar", "star", "bookmark", "flag", "heart", "award", "thumbs-up", "thumbs-down"].map((iconName) => (
                          <DropdownMenu.Item
                            key={iconName}
                            onSelect={() => setIconIdentifier(iconName)}
                            className="flex items-center justify-center p-2 hover:bg-secondary rounded cursor-pointer outline-none transition-colors"
                            title={iconName}
                          >
                            <DynamicIcon name={iconName} className="w-5 h-5 text-foreground" />
                          </DropdownMenu.Item>
                        ))}
                      </div>
                      <div className="mt-2 pt-2 border-t border-border">
                        <input
                          type="text"
                          value={iconIdentifier}
                          onChange={(e) => setIconIdentifier(e.target.value)}
                          className="w-full px-2 py-1 bg-secondary border border-border rounded-md text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground/50"
                          placeholder="Or type lucide name..."
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            </div>

            {/* ROW 2: Description */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={createMutation.isPending || updateMutation.isPending}
                aria-label="Tag description"
                className="w-full px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-muted-foreground/50 disabled:opacity-50"
                placeholder="Optional description..."
              />
            </div>

            {/* ROW 3: Color */}
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Color
              </label>
              <div className="flex flex-wrap gap-2 pt-1">
                {THEME_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={"color " + c}
                    aria-pressed={colorHex === c}
                    onClick={() => setColorHex(c)}
                    className={"w-6 h-6 rounded-full transition-all " + (
                      colorHex === c
                        ? "ring-2 ring-offset-2 ring-offset-background ring-primary scale-110"
                        : "hover:scale-110 opacity-80"
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="btn-primary disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? "Saving..."
                  : "Save"}
              </button>
            </div>
          </form>
        </div>
      ) : taxonomies?.length === 0 ? (
        <div className="solid-card overflow-hidden">
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No tags yet</p>
            <p className="text-sm">
              Create your first tag to start categorizing your trades.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {taxonomies?.map((tax) => (
            <div
              key={tax.id}
              onClick={() => handleView(tax)}
              className="p-4 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col cursor-pointer"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: tax.color_hex }}
                  />
                  {tax.icon_identifier && (
                    <DynamicIcon name={tax.icon_identifier} className="w-4 h-4 text-muted-foreground" />
                  )}
                  <h3 className="font-medium truncate">{tax.name}</h3>
                </div>
                <div className="flex items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                  <button
                    aria-label={`Edit ${tax.name}`}
                    onClick={() => handleEdit(tax)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    aria-label={`Delete ${tax.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleView(tax);
                      void handleDeleteClick(tax);
                    }}
                    className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {getDisplayScope(tax.scope)}
                </span>
                {tax.is_archived && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium surface-warning text-warning border">
                    <Archive className="w-3 h-3" /> Archived
                  </span>
                )}
              </div>

              {tax.description && (
                <p className="text-sm text-muted-foreground line-clamp-2 mt-auto">
                  {tax.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
