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
import { GitMerge } from "lucide-react";

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
    <div className="sticky top-0 z-20 flex items-center gap-3 px-4 py-3 bg-secondary border border-border dark:border-border rounded-xl shadow-lg">
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
  );
}
