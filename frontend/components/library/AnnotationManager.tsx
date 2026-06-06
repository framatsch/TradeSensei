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

import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, ArchiveRestore, Loader2, X, AlertCircle, ArrowLeft, Edit3, ChevronDown, Check } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { toast } from "react-hot-toast";
import {
  useGetAnnotationDefinitions,
  useCreateAnnotationDefinition,
  useUpdateAnnotationDefinition,
  useDeleteAnnotationDefinition,
  useArchiveAnnotationDefinition,
  useUnarchiveAnnotationDefinition,
  fetchAnnotationDefinitionAssignmentCount,
} from "@/hooks/useAnnotationDefinitions";
import type { AnnotationDefinitionResponse, AnnotationDefinitionCreate, AnnotationDefinitionUpdate } from "@/lib/api/types.gen";

type AnnotationType = "int" | "float" | "bool" | "string_enum";

function buildScaleLabels(
  type: AnnotationType,
  minVal: string,
  maxVal: string,
  options: string[],
): Record<string, unknown> | null {
  if (type === "string_enum") {
    const filtered = options.filter((o) => o.trim() !== "");
    return filtered.length > 0 ? { options: filtered } : null;
  }
  if (type === "int" || type === "float") {
    const result: Record<string, number> = {};
    if (minVal.trim() !== "") result.min = Number(minVal);
    if (maxVal.trim() !== "") result.max = Number(maxVal);
    return Object.keys(result).length > 0 ? result : null;
  }
  return null;
}

function parseScaleLabels(
  type: AnnotationType,
  scale_labels: Record<string, unknown> | null | undefined,
): { minVal: string; maxVal: string; options: string[] } {
  if (!scale_labels) return { minVal: "", maxVal: "", options: [""] };
  if (type === "string_enum") {
    const opts = Array.isArray(scale_labels.options) ? (scale_labels.options as string[]) : [];
    return { minVal: "", maxVal: "", options: opts.length > 0 ? opts : [""] };
  }
  if (type === "int" || type === "float") {
    return {
      minVal: scale_labels.min != null ? String(scale_labels.min) : "",
      maxVal: scale_labels.max != null ? String(scale_labels.max) : "",
      options: [""],
    };
  }
  return { minVal: "", maxVal: "", options: [""] };
}

function getDisplayScope(scopeStr: string): string {
  if (!scopeStr) return "";
  if (scopeStr === "both") return "Trades & Check-ins";
  return scopeStr
    .split(",")
    .map((s) => {
      const part = s.trim();
      if (part === "trades") return "Trades";
      if (part === "checkins") return "Check-ins";
      return part;
    })
    .join(", ");
}

import { DynamicIcon } from "@/components/ui/DynamicIcon";

export function AnnotationManager() {
  const [showArchived, setShowArchived] = useState(false);
  const { data: annotations, isLoading, error } = useGetAnnotationDefinitions(undefined, showArchived);
  const createMutation = useCreateAnnotationDefinition();
  const updateMutation = useUpdateAnnotationDefinition();
  const deleteMutation = useDeleteAnnotationDefinition();
  const archiveMutation = useArchiveAnnotationDefinition();
  const unarchiveMutation = useUnarchiveAnnotationDefinition();

  const [isViewing, setIsViewing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedAnnotation, setSelectedAnnotation] = useState<AnnotationDefinitionResponse | null>(null);
  
  // Inline delete confirmation
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Danger Zone states
  const [assignmentCounts, setAssignmentCounts] = useState<{
    trade_count: number;
    checkin_count: number;
    total_count: number;
  } | null>(null);
  const [isFetchingCounts, setIsFetchingCounts] = useState(false);
  const [confirmNameInput, setConfirmNameInput] = useState("");

  // Form state
  const [name, setName] = useState("");
  const [type, setType] = useState<AnnotationType>("int");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["trades"]);
  const [description, setDescription] = useState("");
  const [iconIdentifier, setIconIdentifier] = useState("");

  // Structured scale_labels state
  const [minVal, setMinVal] = useState("");
  const [maxVal, setMaxVal] = useState("");
  const [options, setOptions] = useState<string[]>([""]);

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
        Error loading annotation definitions.
      </div>
    );
  }

  const handleView = (annotation: AnnotationDefinitionResponse) => {
    setSelectedAnnotation(annotation);
    setIsViewing(true);
    setIsEditing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCloseDetails = () => {
    setIsViewing(false);
    setSelectedAnnotation(null);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleEdit = (annotation: AnnotationDefinitionResponse) => {
    setSelectedAnnotation(annotation);
    setName(annotation.name);
    setType(annotation.type);
    
    // Parse annotation.scope into selectedScopes array
    let parsedScopes: string[] = [];
    if (annotation.scope === "both") {
      parsedScopes = ["trades", "checkins"];
    } else {
      parsedScopes = [annotation.scope];
    }
    setSelectedScopes(parsedScopes);
    
    setDescription(annotation.description || "");
    setIconIdentifier(annotation.icon_identifier || "");
    const parsed = parseScaleLabels(
      annotation.type,
      annotation.scale_labels as Record<string, unknown> | null | undefined,
    );
    setMinVal(parsed.minVal);
    setMaxVal(parsed.maxVal);
    setOptions(parsed.options);
    setIsEditing(true);
    setIsViewing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCreate = () => {
    setSelectedAnnotation(null);
    setName("");
    setType("int");
    setSelectedScopes(["trades"]);
    setDescription("");
    setIconIdentifier("");
    setMinVal("");
    setMaxVal("");
    setOptions([""]);
    setIsEditing(true);
    setIsViewing(false);
    setConfirmDeleteId(null);
    setAssignmentCounts(null);
    setConfirmNameInput("");
  };

  const handleCancel = () => {
    setIsEditing(false);
    if (selectedAnnotation) {
      setIsViewing(true);
    } else {
      setSelectedAnnotation(null);
    }
  };

  const handleTypeChange = (newType: AnnotationType) => {
    setType(newType);
    setMinVal("");
    setMaxVal("");
    setOptions([""]);
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

    // Map selected scopes back to "both" | "trades" | "checkins"
    let scopePayload: "trades" | "checkins" | "both" = "trades";
    if (selectedScopes.includes("trades") && selectedScopes.includes("checkins")) {
      scopePayload = "both";
    } else if (selectedScopes.includes("checkins")) {
      scopePayload = "checkins";
    }

    const scaleLabels = buildScaleLabels(type, minVal, maxVal, options);

    try {
      if (selectedAnnotation && isEditing) {
        const payload: AnnotationDefinitionUpdate = {
          name: name.trim(),
          scope: scopePayload,
          description: description.trim() || null,
          scale_labels: scaleLabels as Record<string, unknown> | null,
          icon_identifier: iconIdentifier.trim() || null,
        };
        await updateMutation.mutateAsync({
          definitionId: selectedAnnotation.id,
          payload,
        });

        // Update local detail view data
        const updatedAnnotation: AnnotationDefinitionResponse = {
          ...selectedAnnotation,
          name: name.trim(),
          scope: scopePayload,
          description: description.trim() || null,
          scale_labels: scaleLabels as any,
          icon_identifier: iconIdentifier.trim() || null,
        };
        setSelectedAnnotation(updatedAnnotation);
      } else {
        const payload: AnnotationDefinitionCreate = {
          name: name.trim(),
          type,
          scope: scopePayload,
          description: description.trim() || null,
          scale_labels: scaleLabels as Record<string, unknown> | null,
          icon_identifier: iconIdentifier.trim() || null,
        };
        await createMutation.mutateAsync(payload);
      }
      setIsEditing(false);
      setIsViewing(selectedAnnotation !== null);
    } catch (err: any) {
      console.error(err);
      const errMsg = err?.response?.data?.detail || err?.message || "Failed to save metric. Please try again.";
      toast.error(errMsg);
    }
  };

  const handleArchiveToggle = async (annotation: AnnotationDefinitionResponse) => {
    try {
      if (annotation.is_archived) {
        const updated = await unarchiveMutation.mutateAsync({ definitionId: annotation.id });
        setSelectedAnnotation(updated);
      } else {
        const updated = await archiveMutation.mutateAsync({ definitionId: annotation.id });
        setSelectedAnnotation(updated);
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || "Failed to update archive status.";
      toast.error(errMsg);
    }
  };

  const handleDeleteClick = async (annotation: AnnotationDefinitionResponse) => {
    setConfirmDeleteId(annotation.id);
    setConfirmNameInput("");
    setIsFetchingCounts(true);
    try {
      const counts = await fetchAnnotationDefinitionAssignmentCount(annotation.id);
      setAssignmentCounts(counts);
    } catch (err) {
      console.error("Failed to fetch metric assignment counts:", err);
      setAssignmentCounts({ trade_count: 0, checkin_count: 0, total_count: 0 });
    } finally {
      setIsFetchingCounts(false);
    }
  };

  const handleDeleteConfirm = async (annotation: AnnotationDefinitionResponse) => {
    try {
      const hasAssignments = assignmentCounts && assignmentCounts.total_count > 0;
      await deleteMutation.mutateAsync({
        definitionId: annotation.id,
        force: hasAssignments ? true : false,
      });
      setConfirmDeleteId(null);
      setAssignmentCounts(null);
      setConfirmNameInput("");
      if (selectedAnnotation?.id === annotation.id) {
        handleCloseDetails();
      }
    } catch (err: any) {
      console.error(err);
      setConfirmDeleteId(null);
      setAssignmentCounts(null);
      setConfirmNameInput("");
      const errMsg = err?.response?.data?.detail || "Could not delete metric.";
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
              onClick={() => setShowArchived((v) => !v)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                showArchived ? "bg-primary" : "bg-secondary border border-border"
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                  showArchived ? "translate-x-4" : "translate-x-1"
                }`}
              />
            </div>
            <span className="text-sm text-muted-foreground">Show Archived</span>
          </label>
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Metric
          </button>
        </div>
      )}

      {isViewing && selectedAnnotation && !isEditing ? (
        /* Read-Only Details View modeled after Playbooks */
        <div className="p-6 border border-border rounded-xl bg-card space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={handleCloseDetails}
                className="p-1.5 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                aria-label="Back to list"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="w-1.5 h-6 bg-muted-foreground/30 rounded-full flex-shrink-0" />
              {selectedAnnotation.icon_identifier && (
                <DynamicIcon name={selectedAnnotation.icon_identifier} className="w-5 h-5 text-muted-foreground" />
              )}
              <h3 className="text-xl font-semibold text-foreground">{selectedAnnotation.name}</h3>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleEdit(selectedAnnotation)}
                className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors shrink-0"
              >
                <Edit3 className="w-4 h-4" />
                Edit
              </button>
              <button
                onClick={() => void handleArchiveToggle(selectedAnnotation)}
                disabled={archiveMutation.isPending || unarchiveMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary border border-border rounded-lg transition-colors disabled:opacity-50"
              >
                {selectedAnnotation.is_archived ? (
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
                onClick={() => void handleDeleteClick(selectedAnnotation)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-destructive hover:text-destructive-foreground hover:bg-destructive border border-destructive/30 rounded-lg transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          </div>

          {/* Delete area in details view */}
          {confirmDeleteId === selectedAnnotation.id && (
            <div className="border-t border-b border-border py-4">
              {isFetchingCounts ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing metric usage...
                </div>
              ) : assignmentCounts && assignmentCounts.total_count > 0 ? (
                /* RED DANGER ZONE for active assignments */
                <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30 space-y-3">
                  <div className="flex items-start gap-2.5 text-sm">
                    <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
                    <div className="text-foreground flex-1 space-y-1">
                      <p className="font-semibold text-destructive uppercase tracking-wide text-xs">
                        Danger Zone: Metric is in use!
                      </p>
                      <p className="text-sm">
                        This metric is currently assigned to:
                      </p>
                      <ul className="list-disc pl-5 text-xs space-y-0.5 font-medium">
                        {assignmentCounts.trade_count > 0 && (
                          <li>{assignmentCounts.trade_count} trade(s)</li>
                        )}
                        {assignmentCounts.checkin_count > 0 && (
                          <li>{assignmentCounts.checkin_count} check-in(s)</li>
                        )}
                      </ul>
                      <p className="text-xs text-muted-foreground pt-1">
                        Deleting this metric will **permanently remove all of these assignments and recorded values** from your trades and check-ins! This action cannot be undone.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-1 border-t border-destructive/20">
                    <label className="block text-xs font-medium text-muted-foreground">
                      Type the name of the metric <span className="font-bold text-foreground select-all">&ldquo;{selectedAnnotation.name}&rdquo;</span> to confirm:
                    </label>
                    <input
                      type="text"
                      value={confirmNameInput}
                      onChange={(e) => setConfirmNameInput(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-destructive/30 rounded-md text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-destructive placeholder-muted-foreground/30"
                      placeholder="Metric name"
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
                      onClick={() => void handleDeleteConfirm(selectedAnnotation)}
                      disabled={deleteMutation.isPending || confirmNameInput !== selectedAnnotation.name}
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
                    Are you sure you want to delete metric &ldquo;{selectedAnnotation.name}&rdquo;?
                  </span>
                  <button
                    onClick={() => void handleDeleteConfirm(selectedAnnotation)}
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
            {/* Row 1: Status, Scope, Type structured in a gorgeous 3-column sub-grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Status
                </h4>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${
                    selectedAnnotation.is_archived
                      ? "bg-warning/10 text-warning border-warning/30"
                      : "bg-success/10 text-success border-success/30"
                  }`}
                >
                  {selectedAnnotation.is_archived ? "Archived" : "Active"}
                </span>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Scopes
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedAnnotation.scope === "both" ? (
                    <>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-foreground border border-border">
                        Trades
                      </span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-foreground border border-border">
                        Check-ins
                      </span>
                    </>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-foreground border border-border uppercase">
                      {selectedAnnotation.scope === "checkins" ? "Check-ins" : "Trades"}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                  Type
                </h4>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary border border-primary/20 uppercase">
                  {selectedAnnotation.type}
                </span>
              </div>
            </div>

            {/* Row 2: Description presented as a clean 1-line text container box */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Description
              </h4>
              <div className="w-full bg-secondary/20 px-3 py-2 border border-border/50 rounded-lg text-sm text-muted-foreground truncate">
                {selectedAnnotation.description || (
                  <span className="italic text-muted-foreground/30">No description provided.</span>
                )}
              </div>
            </div>

            {/* Row 3: Options or Value Range details */}
            {selectedAnnotation.scale_labels && (
              <div>
                {selectedAnnotation.type === "string_enum" && Array.isArray((selectedAnnotation.scale_labels as Record<string, unknown>).options) ? (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                      Options
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {((selectedAnnotation.scale_labels as Record<string, unknown>).options as string[]).map((opt) => (
                        <span
                          key={opt}
                          className="px-2.5 py-1 rounded-md text-xs font-medium bg-secondary text-foreground border border-border shadow-sm"
                        >
                          {opt}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : (selectedAnnotation.type === "int" || selectedAnnotation.type === "float") ? (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                      Value Range
                    </h4>
                    <div className="text-sm font-medium text-foreground bg-secondary/50 inline-flex px-2.5 py-0.5 rounded border border-border/50">
                      {(selectedAnnotation.scale_labels as Record<string, unknown>).min != null
                        ? String((selectedAnnotation.scale_labels as Record<string, unknown>).min)
                        : "–"}{" "}
                      &ndash;{" "}
                      {(selectedAnnotation.scale_labels as Record<string, unknown>).max != null
                        ? String((selectedAnnotation.scale_labels as Record<string, unknown>).max)
                        : "–"}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>
      ) : isEditing ? (
        <div className="p-4 border border-border rounded-xl bg-card">
          <h3 className="text-lg font-medium mb-4">
            {selectedAnnotation ? "Edit Metric" : "Create Metric"}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Type
                </label>
                <select
                  value={type}
                  onChange={(e) => handleTypeChange(e.target.value as AnnotationType)}
                  disabled={!!selectedAnnotation}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground disabled:opacity-50"
                >
                  <option value="int">Integer (e.g. Rating 1–5)</option>
                  <option value="float">Float (e.g. Risk Multiple)</option>
                  <option value="bool">Boolean (Yes / No)</option>
                  <option value="string_enum">Enum (Multiple Choice)</option>
                </select>
                {selectedAnnotation && (
                  <p className="text-xs mt-1 text-muted-foreground">
                    Type cannot be changed after creation.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button 
                      type="button"
                      className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
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
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            </div>

            {/* Scale labels — structured per type */}
            {(type === "int" || type === "float") && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Value range <span className="font-normal">(optional)</span>
                </label>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <input
                      type="number"
                      value={minVal}
                      onChange={(e) => setMinVal(e.target.value)}
                      step={type === "float" ? "0.01" : "1"}
                      placeholder="Min"
                      className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                    />
                  </div>
                  <span className="text-muted-foreground text-sm">–</span>
                  <div className="flex-1">
                    <input
                      type="number"
                      value={maxVal}
                      onChange={(e) => setMaxVal(e.target.value)}
                      step={type === "float" ? "0.01" : "1"}
                      placeholder="Max"
                      className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                    />
                  </div>
                </div>
                <p className="text-xs mt-1 text-muted-foreground">
                  Used to validate values when assigning this metric.
                </p>
              </div>
            )}

            {type === "string_enum" && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Options
                </label>
                <div className="space-y-2">
                  {options.map((opt, idx) => (
                    <div key={`option-${idx}`} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={opt}
                        onChange={(e) => {
                          const next = [...options];
                          next[idx] = e.target.value;
                          setOptions(next);
                        }}
                        placeholder={`Option ${idx + 1}`}
                        className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                      />
                      {options.length > 1 && (
                        <button
                          type="button"
                          aria-label={`Remove option ${idx + 1}`}
                          onClick={() => setOptions(options.filter((_, i) => i !== idx))}
                          className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setOptions([...options, ""])}
                    className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                  >
                    <Plus className="w-3 h-3" /> Add option
                  </button>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Description & Icon
              </label>
              <div className="flex gap-4">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  aria-label="Metric description"
                  className="flex-1 px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground resize-y"
                  placeholder="Optional description..."
                />
                
                <div className="w-1/3 relative h-[38px]">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    <DynamicIcon name={iconIdentifier || "tag"} className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={iconIdentifier}
                    onChange={(e) => setIconIdentifier(e.target.value)}
                    aria-label="Icon identifier"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="lucide icon (e.g. tag)"
                  />
                </div>
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
                className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </div>
      ) : annotations?.length === 0 ? (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No metrics yet</p>
            <p className="text-sm">
              Create your first metric to start tracking custom quantitative data on your trades.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {annotations?.map((ann) => (
            <div
              key={ann.id}
              onClick={() => handleView(ann)}
              className="p-4 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col gap-2 cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-4 bg-muted-foreground/30 rounded-full flex-shrink-0" />
                  {ann.icon_identifier && (
                    <DynamicIcon name={ann.icon_identifier} className="w-4 h-4 text-muted-foreground" />
                  )}
                  <h3 className="font-medium truncate">{ann.name}</h3>
                </div>
                <div className="flex items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity shrink-0 ml-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    aria-label={`Edit ${ann.name}`}
                    onClick={() => handleEdit(ann)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    aria-label={`Delete ${ann.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleView(ann);
                      void handleDeleteClick(ann);
                    }}
                    className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary border border-border">
                  {ann.type}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {getDisplayScope(ann.scope)}
                </span>
                {ann.is_archived && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-border">
                    <Archive className="w-3 h-3" /> Archived
                  </span>
                )}
              </div>

              {/* scale_labels display */}
              {ann.scale_labels && (ann.type === "int" || ann.type === "float") && (
                <div className="text-xs text-muted-foreground">
                  Range:{" "}
                  {(ann.scale_labels as Record<string, unknown>).min != null
                    ? String((ann.scale_labels as Record<string, unknown>).min)
                    : "–"}{" "}
                  &ndash;{" "}
                  {(ann.scale_labels as Record<string, unknown>).max != null
                    ? String((ann.scale_labels as Record<string, unknown>).max)
                    : "–"}
                </div>
              )}
              {ann.scale_labels &&
                ann.type === "string_enum" &&
                Array.isArray((ann.scale_labels as Record<string, unknown>).options) && (
                  <div className="flex flex-wrap gap-1">
                    {((ann.scale_labels as Record<string, unknown>).options as string[]).map((opt) => (
                      <span
                        key={opt}
                        className="px-1.5 py-0.5 rounded text-xs bg-secondary text-secondary-foreground border border-border"
                      >
                        {opt}
                      </span>
                    ))}
                  </div>
                )}

              {ann.description && (
                <p className="text-sm text-muted-foreground line-clamp-2 mt-auto">
                  {ann.description}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
