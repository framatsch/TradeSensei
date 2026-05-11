"use client";

import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, Loader2 } from "lucide-react";
import {
  useGetAnnotationDefinitions,
  useCreateAnnotationDefinition,
  useUpdateAnnotationDefinition,
  useDeleteAnnotationDefinition,
} from "@/hooks/useAnnotationDefinitions";
import type { AnnotationDefinitionResponse, AnnotationDefinitionCreate, AnnotationDefinitionUpdate } from "@/lib/api/types.gen";

export function AnnotationManager() {
  const { data: annotations, isLoading, error } = useGetAnnotationDefinitions();
  const createMutation = useCreateAnnotationDefinition();
  const updateMutation = useUpdateAnnotationDefinition();
  const deleteMutation = useDeleteAnnotationDefinition();

  const [isEditing, setIsEditing] = useState(false);
  const [editingAnnotation, setEditingAnnotation] = useState<AnnotationDefinitionResponse | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [type, setType] = useState<"int" | "float" | "bool" | "string_enum">("int");
  const [scope, setScope] = useState<"trades" | "checkins" | "both">("trades");
  const [description, setDescription] = useState("");
  const [scaleLabelsJson, setScaleLabelsJson] = useState("");
  const [jsonError, setJsonError] = useState("");

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-950 text-red-500 rounded-lg">
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
    setScaleLabelsJson(annotation.scale_labels ? JSON.stringify(annotation.scale_labels, null, 2) : "");
    setJsonError("");
    setIsEditing(true);
  };

  const handleCreate = () => {
    setEditingAnnotation(null);
    setName("");
    setType("int");
    setScope("trades");
    setDescription("");
    setScaleLabelsJson("");
    setJsonError("");
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditingAnnotation(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    let parsedScaleLabels = null;
    if (scaleLabelsJson.trim() && type === "string_enum") {
      try {
        parsedScaleLabels = JSON.parse(scaleLabelsJson);
        setJsonError("");
      } catch (err) {
        setJsonError("Invalid JSON format");
        return;
      }
    }

    try {
      if (editingAnnotation) {
        const payload: AnnotationDefinitionUpdate = {
          name: name.trim(),
          scope,
          description: description.trim() || null,
        };
        if (type === "string_enum") {
          payload.scale_labels = parsedScaleLabels;
        } else {
            payload.scale_labels = null;
        }
        // type cannot be changed once created on backend, so we don't send it or send the same
        
        await updateMutation.mutateAsync({
          definitionId: editingAnnotation.id,
          payload,
        });
      } else {
        const payload: AnnotationDefinitionCreate = {
          name: name.trim(),
          type,
          scope,
        };
        if (description.trim()) {
          payload.description = description.trim();
        }
        if (type === "string_enum" && parsedScaleLabels) {
          payload.scale_labels = parsedScaleLabels;
        }
        await createMutation.mutateAsync(payload);
      }
      setIsEditing(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (annotation: AnnotationDefinitionResponse) => {
    if (!window.confirm(`Are you sure you want to delete "${annotation.name}"?`)) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(annotation.id);
    } catch (err) {
      console.error(err);
      alert("Could not delete. It may be in use (archived instead).");
    }
  };

  return (
    <div className="space-y-6">
      {!isEditing && (
        <div className="flex justify-end">
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Metric
          </button>
        </div>
      )}

      {isEditing ? (
        <div className="p-4 border border-border dark:border-border rounded-xl bg-card">
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
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Type
                </label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value as "int" | "float" | "bool" | "string_enum")}
                  disabled={!!editingAnnotation} // type is immutable after creation
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-sm disabled:opacity-50"
                >
                  <option value="int">Integer (e.g. Rating 1-5)</option>
                  <option value="float">Float (e.g. Risk Multiple)</option>
                  <option value="bool">Boolean (Yes/No)</option>
                  <option value="string_enum">Enum (Multiple Choice)</option>
                </select>
                {editingAnnotation && <p className="text-xs mt-1 text-muted-foreground">Type cannot be changed after creation.</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value as "trades" | "checkins" | "both")}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-sm"
                >
                  <option value="trades">Trades</option>
                  <option value="checkins">Check-ins</option>
                  <option value="both">Both</option>
                </select>
              </div>
            </div>

            {type === "string_enum" && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scale Labels (JSON array of options)
                </label>
                <textarea
                  value={scaleLabelsJson}
                  onChange={(e) => setScaleLabelsJson(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 font-mono rounded-lg bg-secondary border border-border dark:border-border text-sm resize-y"
                  placeholder='{"options": ["A", "B", "C"]}'
                />
                {jsonError && <p className="mt-1 text-xs text-red-400">{jsonError}</p>}
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
                className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-sm resize-none"
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
                className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-lg disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? "Saving..."
                  : "Save"}
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
              className="p-4 rounded-xl border border-border dark:border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium truncate">{ann.name}</h3>
                </div>
                <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleEdit(ann)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(ann)}
                    className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-500 border border-border">
                  {ann.type}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {ann.scope}
                </span>
                {ann.is_archived && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-500">
                    <Archive className="w-3 h-3" /> Archived
                  </span>
                )}
              </div>

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