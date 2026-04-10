/**
 * BulkActionToolbar — sticky bar that appears when trades are selected.
 */

"use client";

import { Spinner } from "@/components/ui/Spinner";
import { GitMerge } from "lucide-react";

interface Props {
  selectedCount: number;
  onDelete: () => void;
  onAssignTag: () => void;
  onAssignPlaybook: () => void;
  onMerge?: () => void;
  isDeleting?: boolean;
}

export function BulkActionToolbar({
  selectedCount,
  onDelete,
  onAssignTag,
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
        onClick={onAssignTag}
        className="px-3 py-1.5 bg-zinc-200 dark:bg-zinc-600 hover:bg-zinc-500 text-foreground rounded-md text-sm transition-colors"
      >
        Assign Tag
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
