"use client";

import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, Loader2, X, AlertCircle } from "lucide-react";
import { toast } from "react-hot-toast";
import {
  useGetAnnotationDefinitions,
  useCreateAnnotationDefinition,
  useUpdateAnnotationDefinition,
  useDeleteAnnotationDefinition,
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

export function AnnotationManager() {
  const { data: annotations, isLoading, error } = useGetAnnotationDefinitions();
  const createMutation = useCreateAnnotationDefinition();
  const updateMutation = useUpdateAnnotationDefinition();
  const deleteMutation = useDeleteAnnotationDefinition();

  const [isEditing, setIsEditing] = useState(false);
  const [editingAnnotation, setEditingAnnotation] = useState<AnnotationDefinitionResponse | null>(null);
  // Inline delete confirmation: holds the id of the annotation pending deletion
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [type, setType] = useState<AnnotationType>("int");
  const [scope, setScope] = useState<"trades" | "checkins" | "both">("trades");
  const [description, setDescription] = useState("");

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

  const handleEdit = (annotation: AnnotationDefinitionResponse) => {
    setEditingAnnotation(annotation);
    setName(annotation.name);
    setType(annotation.type);
    setScope(annotation.scope);
    setDescription(annotation.description || "");
    const parsed = parseScaleLabels(
      annotation.type,
      annotation.scale_labels as Record<string, unknown> | null | undefined,
    );
    setMinVal(parsed.minVal);
    setMaxVal(parsed.maxVal);
    setOptions(parsed.options);
    setIsEditing(true);
  };

  const handleCreate = () => {
    setEditingAnnotation(null);
    setName("");
    setType("int");
    setScope("trades");
    setDescription("");
    setMinVal("");
    setMaxVal("");
    setOptions([""]);
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditingAnnotation(null);
  };

  const handleTypeChange = (newType: AnnotationType) => {
    setType(newType);
    setMinVal("");
    setMaxVal("");
    setOptions([""]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const scaleLabels = buildScaleLabels(type, minVal, maxVal, options);

    try {
      if (editingAnnotation) {
        const payload: AnnotationDefinitionUpdate = {
          name: name.trim(),
          scope,
          description: description.trim() || null,
          scale_labels: scaleLabels,
        };
        await updateMutation.mutateAsync({
          definitionId: editingAnnotation.id,
          payload,
        });
      } else {
        const payload: AnnotationDefinitionCreate = {
          name: name.trim(),
          type,
          scope,
          description: description.trim() || null,
          scale_labels: scaleLabels,
        };
        await createMutation.mutateAsync(payload);
      }
      setIsEditing(false);
    } catch (err) {
      console.error(err);
      toast.error("Failed to save metric. Please try again.");
    }
  };

  const handleDeleteConfirm = async (annotation: AnnotationDefinitionResponse) => {
    try {
      await deleteMutation.mutateAsync(annotation.id);
      setConfirmDeleteId(null);
    } catch (err) {
      console.error(err);
      setConfirmDeleteId(null);
      toast.error("Could not delete — it may be in use. It has been archived instead.");
    }
  };

  return (
    <div className="space-y-6">
      {!isEditing && (
        <div className="flex justify-end">
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Metric
          </button>
        </div>
      )}

      {isEditing ? (
        <div className="p-4 border border-border rounded-xl bg-card">
          <h3 className="text-lg font-medium mb-4">
            {editingAnnotation ? "Edit Metric" : "Create Metric"}
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
                  disabled={!!editingAnnotation}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground disabled:opacity-50"
                >
                  <option value="int">Integer (e.g. Rating 1–5)</option>
                  <option value="float">Float (e.g. Risk Multiple)</option>
                  <option value="bool">Boolean (Yes / No)</option>
                  <option value="string_enum">Enum (Multiple Choice)</option>
                </select>
                {editingAnnotation && (
                  <p className="text-xs mt-1 text-muted-foreground">
                    Type cannot be changed after creation.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value as "trades" | "checkins" | "both")}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                >
                  <option value="trades">Trades</option>
                  <option value="checkins">Check-ins</option>
                  <option value="both">Both</option>
                </select>
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
                      step={type === "float" ? "any" : "1"}
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
                      step={type === "float" ? "any" : "1"}
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
                    // Use a stable key based on index — options are only reordered by
                    // explicit deletion, so index is stable within a single edit session.
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
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                aria-label="Metric description"
                className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground resize-none"
                placeholder="Optional description..."
              />
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
              className="p-4 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col gap-2"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-medium truncate">{ann.name}</h3>
                <div className="flex items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity shrink-0 ml-2">
                  <button
                    aria-label={`Edit ${ann.name}`}
                    onClick={() => handleEdit(ann)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    aria-label={`Delete ${ann.name}`}
                    onClick={() => setConfirmDeleteId(ann.id)}
                    className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Inline delete confirmation */}
              {confirmDeleteId === ann.id && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-destructive/10 border border-destructive/20 text-sm">
                  <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
                  <span className="text-foreground flex-1">Delete &ldquo;{ann.name}&rdquo;?</span>
                  <button
                    onClick={() => void handleDeleteConfirm(ann)}
                    disabled={deleteMutation.isPending}
                    className="px-2 py-0.5 text-xs font-medium bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 disabled:opacity-50"
                  >
                    {deleteMutation.isPending ? "…" : "Delete"}
                  </button>
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    className="px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              )}

              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary border border-border">
                  {ann.type}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {ann.scope}
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
