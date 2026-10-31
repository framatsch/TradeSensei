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
 * BulkActionToolbar — sticky bar that appears when trades are selected.
 */

"use client";

import { Spinner } from "@/components/ui/Spinner";
import { BookOpen, GitMerge, Tags, Trash2 } from "lucide-react";

interface Props {
  selectedCount: number;
  onDelete: () => void;
  onAssignTaxonomy: () => void;
  onAssignPlaybook: () => void;
  onMerge?: () => void;
  isDeleting?: boolean;
}

export function BulkActionToolbar({
  selectedCount,
  onDelete,
  onAssignTaxonomy,
  onAssignPlaybook,
  onMerge,
  isDeleting = false,
}: Props) {
  if (selectedCount === 0) return null;

  return (
    <>
    <div className="sticky top-0 z-20 hidden items-center gap-3 px-4 py-3 bg-secondary border border-border rounded-xl shadow-lg lg:flex">
      <span className="text-sm font-medium text-foreground mr-auto">
        {selectedCount} {selectedCount === 1 ? "trade" : "trades"} selected
      </span>

      {onMerge && selectedCount >= 2 && (
        <button
          type="button"
          onClick={onMerge}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#6063dd] hover:opacity-90 text-white rounded-md text-sm transition-colors"
        >
          <GitMerge size={14} />
          Merge
        </button>
      )}

      <button
        type="button"
        onClick={onAssignPlaybook}
        className="px-3 py-1.5 bg-zinc-200 dark:bg-zinc-600 hover:bg-zinc-500 text-foreground rounded-md text-sm transition-colors"
      >
        Assign Playbook
      </button>

      <button
        type="button"
        onClick={onAssignTaxonomy}
        className="px-3 py-1.5 bg-zinc-200 dark:bg-zinc-600 hover:bg-zinc-500 text-foreground rounded-md text-sm transition-colors"
      >
        Assign Taxonomy
      </button>

      <button
        type="button"
        onClick={onDelete}
        disabled={isDeleting}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-red-700 hover:bg-red-600 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-md text-sm transition-colors"
      >
        {isDeleting && <Spinner size="sm" />}
        Delete
      </button>
    </div>
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card px-3 pt-2 pb-[env(safe-area-inset-bottom)] shadow-lg lg:hidden" role="toolbar" aria-label="Selected trade actions">
      <p className="mb-1 text-xs text-foreground"><span className="font-mono font-medium">{selectedCount}</span> selected</p>
      <div className="flex items-center gap-2 pb-2">
        {onMerge && selectedCount >= 2 && (
          <button type="button" onClick={onMerge} className="btn-primary min-h-11 min-w-0 flex-1 flex-col gap-1 px-2 py-2 text-[11px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <GitMerge className="h-4 w-4" aria-hidden="true" />
            Merge
          </button>
        )}
        <button type="button" onClick={onAssignPlaybook} className="btn-ghost min-h-11 min-w-0 flex-1 flex-col gap-1 px-2 py-2 text-[11px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <BookOpen className="h-4 w-4" aria-hidden="true" />
          Playbook
        </button>
        <button type="button" onClick={onAssignTaxonomy} className="btn-ghost min-h-11 min-w-0 flex-1 flex-col gap-1 px-2 py-2 text-[11px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Tags className="h-4 w-4" aria-hidden="true" />
          Tags
        </button>
        <button type="button" onClick={onDelete} disabled={isDeleting} className="btn-ghost min-h-11 min-w-0 flex-1 flex-col gap-1 px-2 py-2 text-[11px] text-danger disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          {isDeleting ? <Spinner size="sm" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
          Delete
        </button>
      </div>
    </div>
    </>
  );
}
