"use client";

import { useState } from "react";
import { Plus, Edit2, Trash2, Archive, Loader2, AlertCircle } from "lucide-react";
import { toast } from "react-hot-toast";
import {
  useGetTaxonomies,
  useCreateTaxonomy,
  useUpdateTaxonomy,
  useDeleteTaxonomy,
} from "@/hooks/useTaxonomies";
import { THEME_COLORS } from "@/lib/constants/colors";
import type { TaxonomyResponse, TaxonomyCreate } from "@/lib/api/types.gen";

export function TaxonomyManager() {
  const { data: taxonomies, isLoading, error } = useGetTaxonomies();
  const createMutation = useCreateTaxonomy();
  const updateMutation = useUpdateTaxonomy();
  const deleteMutation = useDeleteTaxonomy();

  const [isEditing, setIsEditing] = useState(false);
  const [editingTaxonomy, setEditingTaxonomy] = useState<TaxonomyResponse | null>(null);
  // Inline delete confirmation: holds the id of the taxonomy pending deletion
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"trades" | "checkins" | "both" | "playbook">("trades");
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
      <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
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
      toast.error("Failed to save tag. Please try again.");
    }
  };

  const handleDeleteConfirm = async (taxonomy: TaxonomyResponse) => {
    try {
      await deleteMutation.mutateAsync(taxonomy.id);
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
            New Tag
          </button>
        </div>
      )}

      {isEditing ? (
        <div className="p-4 border border-border rounded-xl bg-card">
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
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Scope
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value as "trades" | "checkins" | "both" | "playbook")}
                  className="w-full px-3 py-2 rounded-lg bg-secondary border border-border text-sm text-foreground"
                >
                  <option value="trades">Trades</option>
                  <option value="checkins">Check-ins</option>
                  <option value="both">Both</option>
                  <option value="playbook">Playbook</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                Color
              </label>
              <div className="flex flex-wrap gap-2">
                {THEME_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={`color ${c}`}
                    aria-pressed={colorHex === c}
                    onClick={() => setColorHex(c)}
                    className={`w-6 h-6 rounded-full transition-all ${
                      colorHex === c
                        ? "ring-2 ring-offset-2 ring-offset-background ring-primary scale-110"
                        : "hover:scale-110 opacity-80"
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
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
                aria-label="Tag description"
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
              className="p-4 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow group flex flex-col"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: tax.color_hex }}
                  />
                  <h3 className="font-medium truncate">{tax.name}</h3>
                </div>
                <div className="flex items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                  <button
                    aria-label={`Edit ${tax.name}`}
                    onClick={() => handleEdit(tax)}
                    className="p-1.5 text-muted-foreground hover:text-primary transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    aria-label={`Delete ${tax.name}`}
                    onClick={() => setConfirmDeleteId(tax.id)}
                    className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Inline delete confirmation */}
              {confirmDeleteId === tax.id && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-destructive/10 border border-destructive/20 text-sm mb-2">
                  <AlertCircle className="w-4 h-4 text-destructive shrink-0" />
                  <span className="text-foreground flex-1">Delete &ldquo;{tax.name}&rdquo;?</span>
                  <button
                    onClick={() => void handleDeleteConfirm(tax)}
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

              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                  {tax.scope}
                </span>
                {tax.is_archived && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-border">
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
