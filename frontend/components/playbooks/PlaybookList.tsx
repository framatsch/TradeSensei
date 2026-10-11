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
 * PlaybookList — table of playbooks with filter bar, sorting, and active status toggle.
 */

"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import {
  usePlaybooks,
  useCreatePlaybook,
  useUpdatePlaybook,
} from "@/hooks/usePlaybooks";
import { Spinner } from "@/components/ui/Spinner";
import {
  PlaybookFilterBar,
  DEFAULT_PLAYBOOK_FILTERS,
  type PlaybookFilters,
} from "./PlaybookFilterBar";

type SortKey = "name" | "created_at" | "is_active";
type SortDirection = "asc" | "desc";

export function PlaybookList() {
  const router = useRouter();
  const { data: playbooks, isLoading, isError, error, refetch } = usePlaybooks();
  const { mutate: create, isPending: creating } = useCreatePlaybook();
  const { mutate: updatePlaybook } = useUpdatePlaybook();
  const UNTITLED_PLAYBOOK_NAME = "Untitled Playbook";

  const [filters, setFilters] = useState<PlaybookFilters>(DEFAULT_PLAYBOOK_FILTERS);
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDirection>("asc");

  const rawPlaybooks = useMemo(() => playbooks ?? [], [playbooks]);

  const totalCounts = useMemo(() => {
    let active = 0;
    let inactive = 0;
    for (const pb of rawPlaybooks) {
      if (pb.is_active) active += 1;
      else inactive += 1;
    }
    return {
      all: rawPlaybooks.length,
      active,
      inactive,
    };
  }, [rawPlaybooks]);

  const filteredAndSorted = useMemo(() => {
    return rawPlaybooks
      .filter((pb) => {
        // Status filter
        if (filters.status === "active" && !pb.is_active) return false;
        if (filters.status === "inactive" && pb.is_active) return false;

        // Search query filter
        if (filters.search.trim()) {
          const q = filters.search.toLowerCase();
          const matchName = pb.name.toLowerCase().includes(q);
          const matchDesc = pb.description?.toLowerCase().includes(q);
          if (!matchName && !matchDesc) return false;
        }

        // Tag filter
        if (filters.tagIds.length > 0) {
          const hasTag = pb.taxonomies?.some((t) => filters.tagIds.includes(t.id));
          if (!hasTag) return false;
        }

        return true;
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortKey === "name") {
          cmp = a.name.localeCompare(b.name);
        } else if (sortKey === "created_at") {
          cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        } else if (sortKey === "is_active") {
          cmp = (a.is_active ? 1 : 0) - (b.is_active ? 1 : 0);
        }
        return sortDir === "asc" ? cmp : -cmp;
      });
  }, [rawPlaybooks, filters, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const getNextUntitledName = () => {
    const existingNames = new Set(rawPlaybooks.map((pb) => pb.name));
    if (!existingNames.has(UNTITLED_PLAYBOOK_NAME)) {
      return UNTITLED_PLAYBOOK_NAME;
    }

    let counter = 2;
    while (existingNames.has(`${UNTITLED_PLAYBOOK_NAME} ${counter}`)) {
      counter += 1;
    }
    return `${UNTITLED_PLAYBOOK_NAME} ${counter}`;
  };

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

  const handleToggleStatus = (id: string, currentStatus: boolean) => {
    updatePlaybook({
      id,
      payload: { is_active: !currentStatus },
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

  return (
    <div className="space-y-4">
      {/* Header action */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Playbooks</h2>
          <p className="text-xs text-muted-foreground">
            Manage your strategy setups, active status, and tags.
          </p>
        </div>
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

      {/* Filter Bar */}
      {rawPlaybooks.length > 0 && (
        <PlaybookFilterBar
          filters={filters}
          onChange={setFilters}
          totalCounts={totalCounts}
        />
      )}

      {/* Table */}
      <div className="solid-card">
        {rawPlaybooks.length === 0 ? (
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No playbooks yet</p>
            <p className="text-sm">
              Create your first playbook to start categorizing trades by strategy.
            </p>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="px-4 py-16 text-center text-muted-foreground">
            <p className="text-base font-medium mb-1">No matching playbooks</p>
            <p className="text-sm mb-4">
              No playbooks match your current filter criteria.
            </p>
            <button
              type="button"
              onClick={() => setFilters(DEFAULT_PLAYBOOK_FILTERS)}
              className="px-3 py-1.5 text-xs font-medium bg-secondary hover:bg-muted text-foreground rounded-md transition-colors"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSort("name")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors uppercase"
                  >
                    Name
                    {sortKey === "name" ? (
                      sortDir === "asc" ? (
                        <ArrowUp className="w-3 h-3 text-primary" />
                      ) : (
                        <ArrowDown className="w-3 h-3 text-primary" />
                      )
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-40" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap">
                  Tags
                </th>
                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSort("is_active")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors uppercase"
                  >
                    Status
                    {sortKey === "is_active" ? (
                      sortDir === "asc" ? (
                        <ArrowUp className="w-3 h-3 text-primary" />
                      ) : (
                        <ArrowDown className="w-3 h-3 text-primary" />
                      )
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-40" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSort("created_at")}
                    className="inline-flex items-center gap-1.5 hover:text-foreground transition-colors uppercase"
                  >
                    Created
                    {sortKey === "created_at" ? (
                      sortDir === "asc" ? (
                        <ArrowUp className="w-3 h-3 text-primary" />
                      ) : (
                        <ArrowDown className="w-3 h-3 text-primary" />
                      )
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-40" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.map((pb) => (
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
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleStatus(pb.id, pb.is_active);
                      }}
                      className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium transition-all ${
                        pb.is_active
                          ? "bg-success/10 text-success border border-success/30 hover:bg-success/20"
                          : "bg-secondary text-muted-foreground border border-border hover:bg-muted"
                      }`}
                      title={pb.is_active ? "Click to deactivate" : "Click to activate"}
                      aria-label={`Toggle status for ${pb.name}, currently ${pb.is_active ? "Active" : "Inactive"}`}
                    >
                      {pb.is_active ? "Active" : "Inactive"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                    {new Date(pb.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
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
