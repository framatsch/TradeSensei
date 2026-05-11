"use client";

import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, Loader2 } from "lucide-react";
import {
  useGetTaxonomies,
  useCreateTaxonomy,
  useUpdateTaxonomy,
  useDeleteTaxonomy,
} from "@/hooks/useTaxonomies";
import type { TaxonomyResponse, TaxonomyCreate } from "@/lib/api/types.gen";

export function TaxonomyManager() {
  const { data: taxonomies, isLoading, error } = useGetTaxonomies();
  const createMutation = useCreateTaxonomy();
  const updateMutation = useUpdateTaxonomy();
  const deleteMutation = useDeleteTaxonomy();

  const [isEditing, setIsEditing] = useState(false);
  const [editingTaxonomy, setEditingTaxonomy] = useState<TaxonomyResponse | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"trades" | "checkins" | "both">("trades");
  const [colorHex, setColorHex] = useState("#3b82f6");
  const [description, setDescription] = useState("");

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
        Error loading taxonomies.
      </div>
    );
  }

  const handleEdit = (taxonomy: TaxonomyResponse) => {
    setEditingTaxonomy(taxonomy);
    setName(taxonomy.name);
    setScope(taxonomy.scope);
    setColorHex(taxonomy.color_hex);
    setDescription(taxonomy.description || "");
    setIsEditing(true);
  };

  const handleCreate = () => {
    setEditingTaxonomy(null);
    setName("");
    setScope("trades");
    setColorHex("#3b82f6");
    setDescription("");
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditingTaxonomy(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      if (editingTaxonomy) {
        await updateMutation.mutateAsync({
          taxonomyId: editingTaxonomy.id,
          payload: {
            name: name.trim(),
            scope,
            color_hex: colorHex,
            description: description.trim() || null,
          },
        });
      } else {
        const payload: TaxonomyCreate = {
          name: name.trim(),
          scope,
          color_hex: colorHex,
        };
        if (description.trim()) {
          payload.description = description.trim();
        }
        await createMutation.mutateAsync(payload);
      }
      setIsEditing(false);
    } catch (err) {
      console.error(err);
      // Let mutation error state handle UI feedback if needed
    }
  };

  const handleDelete = async (taxonomy: TaxonomyResponse) => {
    if (!window.confirm(`Are you sure you want to delete "${taxonomy.name}"?`)) {
      return;
    }
    try {
      await deleteMutation.mutateAsync(taxonomy.id);
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
            New Tag
          </button>
        </div>
      )}

      {isEditing ? (
        <div className="p-4 border border-border dark:border-border rounded-xl bg-card">
          <h3 className="text-lg font-medium mb-4">
            {editingTaxonomy ? "Edit Tag" : "Create Tag"}
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

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Color
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={colorHex}
                  onChange={(e) => setColorHex(e.target.value)}
                  className="w-10 h-10 p-1 rounded bg-secondary border border-border cursor-pointer"
                />
                <span className="text-sm font-mono text-muted-foreground">{colorHex}</span>
              </div>
            </div>

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
      ) : taxonomies?.length === 0 ? (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
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
              className="p-4 rounded-xl border border-border dark:border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: tax.color_hex }}
                  />
                  <h3 className="font-medium truncate">{tax.name}</h3>
                </div>
                <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleEdit(tax)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(tax)}
                    className="p-1.5 text-muted-foreground hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {tax.scope}
                </span>
                {tax.is_archived && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-500">
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
