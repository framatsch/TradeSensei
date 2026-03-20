/**
 * TagList — chip grid with create form and per-tag delete.
 */

"use client";

import { useState } from "react";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/useTags";
import { TagBadge } from "./TagBadge";
import { Spinner } from "@/components/ui/Spinner";
import type { TagCreate } from "@/lib/types";

const PRESET_COLORS = [
  "#ef4444", // red
  "#f97316", // orange
  "#eab308", // yellow
  "#22c55e", // green
  "#06b6d4", // cyan
  "#3b82f6", // blue
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#64748b", // slate
];

export function TagList() {
  const { data: tags, isLoading, isError, error, refetch } = useTags();
  const { mutate: create, isPending: creating } = useCreateTag();
  const { mutate: remove } = useDeleteTag();

  const [name, setName] = useState("");
  const [color, setColor] = useState(PRESET_COLORS[5]); // default blue
  const [nameError, setNameError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Tag name is required.");
      return;
    }
    setNameError("");
    const payload: TagCreate = { name: trimmed, color };
    create(payload, {
      onSuccess: () => {
        setName("");
        setColor(PRESET_COLORS[5]);
      },
    });
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    remove(id, { onSettled: () => setDeletingId(null) });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-red-400 font-medium mb-2">Failed to load tags.</p>
        <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const items = tags ?? [];

  return (
    <div className="space-y-6">
      {/* Create form */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
          Create New Tag
        </h3>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-48">
            <label
              htmlFor="tag-name"
              className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1"
            >
              Name <span className="text-red-400">*</span>
            </label>
            <input
              id="tag-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (nameError) setNameError("");
              }}
              placeholder="e.g. Earnings Play"
              className="w-full px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            {nameError && (
              <p className="mt-1 text-xs text-red-400">{nameError}</p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Color</p>
            <div className="flex items-center gap-2">
              {/* Preset swatches */}
              <div className="flex items-center gap-1">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className="w-6 h-6 rounded-full border-2 transition-transform hover:scale-110"
                    style={{
                      backgroundColor: c,
                      borderColor: color === c ? "white" : "transparent",
                    }}
                    aria-label={`Select color ${c}`}
                    title={c}
                  />
                ))}
              </div>
              {/* Custom color picker */}
              <label
                className="w-6 h-6 rounded-full border-2 border-slate-300 dark:border-slate-600 cursor-pointer overflow-hidden flex items-center justify-center hover:border-slate-400 transition-colors"
                title="Custom color"
              >
                <span className="sr-only">Custom color</span>
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="opacity-0 absolute w-px h-px"
                />
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="w-3 h-3 text-slate-600 dark:text-slate-400"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="16" />
                  <line x1="8" y1="12" x2="16" y2="12" />
                </svg>
              </label>
              {/* Preview */}
              <div
                className="w-6 h-6 rounded-full border border-slate-300 dark:border-slate-600"
                style={{ backgroundColor: color }}
                aria-hidden="true"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={creating}
            className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {creating ? "Adding…" : "Add Tag"}
          </button>
        </form>
      </div>

      {/* Tags grid */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">
          All Tags
          <span className="ml-2 text-xs font-normal text-slate-500">
            ({items.length})
          </span>
        </h3>

        {items.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">
            No tags yet. Create your first tag above.
          </p>
        ) : (
          <div className="flex flex-wrap gap-3">
            {items.map((tag) => (
              <div key={tag.id} className="flex items-center gap-1.5 group">
                <TagBadge tag={tag} />
                <button
                  onClick={() => handleDelete(tag.id)}
                  disabled={deletingId === tag.id}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded-full text-slate-500 hover:text-red-400 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  title={`Delete tag "${tag.name}"`}
                  aria-label={`Delete tag ${tag.name}`}
                >
                  {deletingId === tag.id ? (
                    <Spinner size="sm" />
                  ) : (
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="w-3.5 h-3.5"
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
