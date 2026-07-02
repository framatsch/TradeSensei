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

/**
 * PlaybookList — table of playbooks with inline create and delete actions.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import {
  usePlaybooks,
  useCreatePlaybook,
  useDeletePlaybook,
} from "@/hooks/usePlaybooks";
import { Spinner } from "@/components/ui/Spinner";

export function PlaybookList() {
  const router = useRouter();
  const { data: playbooks, isLoading, isError, error, refetch } = usePlaybooks();
  const { mutate: create, isPending: creating } = useCreatePlaybook();
  const { mutate: remove } = useDeletePlaybook();
  const UNTITLED_PLAYBOOK_NAME = "Untitled Playbook";

  const getNextUntitledName = () => {
    const existingNames = new Set((playbooks ?? []).map((pb) => pb.name));
    if (!existingNames.has(UNTITLED_PLAYBOOK_NAME)) {
      return UNTITLED_PLAYBOOK_NAME;
    }

    let counter = 2;
    while (existingNames.has(`${UNTITLED_PLAYBOOK_NAME} ${counter}`)) {
      counter += 1;
    }
    return `${UNTITLED_PLAYBOOK_NAME} ${counter}`;
  };

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleCreate = () => {
    const nextUntitledName = getNextUntitledName();

    create(
      { name: nextUntitledName },
      {
        onSuccess: (newPlaybook) => {
          router.push(`/dashboard/library/playbooks/${newPlaybook.id}?edit=true&draft=true`);
        },
        onError: async () => {
          await refetch();
        },
      }
    );
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    remove(id, {
      onSettled: () => {
        setDeletingId(null);
        setConfirmDeleteId(null);
      },
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
      <div className="flex justify-end">
        <button
          onClick={handleCreate}
          disabled={creating}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors disabled:opacity-50"
        >
          {creating ? (
            <Spinner size="sm" />
          ) : (
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
          )}
          New Playbook
        </button>
      </div>

      {/* Table */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        {items.length === 0 ? (
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No playbooks yet</p>
            <p className="text-sm">
              Create your first playbook to start categorizing trades by strategy.
            </p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                {["Name", "Tags", "Status", "Created", ""].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap"
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
                  onClick={() => router.push(`/dashboard/library/playbooks/${pb.id}`)}
                  className="border-b border-border hover:bg-secondary/30 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 text-sm font-medium text-foreground">
                    {pb.name}
                  </td>
                  <td className="px-4 py-3">
                    {pb.taxonomies && pb.taxonomies.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {pb.taxonomies.map((tag) => (
                          <span
                            key={tag.id}
                            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border"
                            style={{
                              backgroundColor: (tag.color_hex ?? "#888") + "20",
                              borderColor: (tag.color_hex ?? "#888") + "50",
                              color: tag.color_hex ?? "#888",
                            }}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="italic text-muted-foreground text-sm">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        pb.is_active
                          ? "bg-success/10 text-success border border-success/30"
                          : "bg-secondary text-muted-foreground border border-border"
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
                      {confirmDeleteId === pb.id ? (
                        <div
                          className="flex items-center gap-1.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <AlertCircle className="w-3.5 h-3.5 text-destructive shrink-0" />
                          <span className="text-xs text-foreground whitespace-nowrap">Delete?</span>
                          <button
                            onClick={() => handleDelete(pb.id)}
                            disabled={deletingId === pb.id}
                            className="px-2 py-0.5 text-xs font-medium bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 disabled:opacity-50"
                          >
                            {deletingId === pb.id ? <Spinner size="sm" /> : "Yes"}
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => router.push(`/dashboard/library/playbooks/${pb.id}?edit=true`)}
                            className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                            title="Edit playbook"
                            aria-label={`Edit ${pb.name}`}
                          >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                              <path d="M12 20h9"></path>
                              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                            </svg>
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(pb.id)}
                            disabled={deletingId === pb.id}
                            className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            title="Delete playbook"
                            aria-label={`Delete ${pb.name}`}
                          >
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
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
