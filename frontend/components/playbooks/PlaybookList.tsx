/**
 * PlaybookList — table of playbooks with inline create and delete actions.
 */

"use client";

import { useState } from "react";
import {
  usePlaybooks,
  useCreatePlaybook,
  useUpdatePlaybook,
  useDeletePlaybook,
} from "@/hooks/usePlaybooks";
import { PlaybookForm } from "./PlaybookForm";
import { Spinner } from "@/components/ui/Spinner";
import type { Playbook, PlaybookCreate } from "@/lib/types";

export function PlaybookList() {
  const { data: playbooks, isLoading, isError, error, refetch } = usePlaybooks();
  const { mutate: create, isPending: creating } = useCreatePlaybook();
  const { mutate: update, isPending: updating } = useUpdatePlaybook();
  const { mutate: remove } = useDeletePlaybook();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreate = (data: PlaybookCreate) => {
    create(data, {
      onSuccess: () => setShowCreateForm(false),
    });
  };

  const handleUpdate = (playbook: Playbook, data: PlaybookCreate) => {
    update(
      { id: playbook.id, payload: data },
      { onSuccess: () => setEditingId(null) }
    );
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    remove(id, {
      onSettled: () => setDeletingId(null),
    });
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
        <p className="text-red-400 font-medium mb-2">Failed to load playbooks.</p>
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const items = playbooks ?? [];

  return (
    <div className="space-y-4">
      {/* Header action */}
      {!showCreateForm && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-4 h-4"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Playbook
          </button>
        </div>
      )}

      {/* Inline create form */}
      {showCreateForm && (
        <div className="bg-card rounded-xl border border-blue-600/40 p-5">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4">
            New Playbook
          </h3>
          <PlaybookForm
            onSubmit={handleCreate}
            onCancel={() => setShowCreateForm(false)}
            isSubmitting={creating}
          />
        </div>
      )}

      {/* Table */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        {items.length === 0 && !showCreateForm ? (
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No playbooks yet</p>
            <p className="text-sm">
              Create your first playbook to start categorizing trades by strategy.
            </p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-background/50">
                {["Name", "Description", "Status", "Created", ""].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((pb) => (
                <tr
                  key={pb.id}
                  className="border-b border-border/50 last:border-0"
                >
                  {editingId === pb.id ? (
                    <td colSpan={5} className="px-4 py-4">
                      <PlaybookForm
                        playbook={pb}
                        onSubmit={(data) => handleUpdate(pb, data)}
                        onCancel={() => setEditingId(null)}
                        isSubmitting={updating}
                      />
                    </td>
                  ) : (
                    <>
                      <td className="px-4 py-3 text-sm font-medium text-foreground">
                        {pb.name}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground max-w-xs truncate">
                        {pb.description ?? (
                          <span className="italic text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            pb.is_active
                              ? "bg-emerald-900/50 text-emerald-400 border border-emerald-800"
                              : "bg-secondary text-muted-foreground border border-border dark:border-border"
                          }`}
                        >
                          {pb.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                        {new Date(pb.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => setEditingId(pb.id)}
                            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                            title="Edit playbook"
                            aria-label={`Edit ${pb.name}`}
                          >
                            <svg
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              className="w-4 h-4"
                            >
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDelete(pb.id)}
                            disabled={deletingId === pb.id}
                            className="p-1.5 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-900/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            title="Delete playbook"
                            aria-label={`Delete ${pb.name}`}
                          >
                            {deletingId === pb.id ? (
                              <Spinner size="sm" />
                            ) : (
                              <svg
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                className="w-4 h-4"
                              >
                                <polyline points="3 6 5 6 21 6" />
                                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                <path d="M10 11v6M14 11v6" />
                                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                              </svg>
                            )}
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
