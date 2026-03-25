/**
 * BulkActionToolbar — sticky bar that appears when trades are selected.
 */

"use client";

import { Spinner } from "@/components/ui/Spinner";

interface Props {
  selectedCount: number;
  onDelete: () => void;
  onAssignTag: () => void;
  onAssignPlaybook: () => void;
  isDeleting?: boolean;
}

export function BulkActionToolbar({
  selectedCount,
  onDelete,
  onAssignTag,
  onAssignPlaybook,
  isDeleting = false,
}: Props) {
  if (selectedCount === 0) return null;

  return (
    <div className="sticky top-0 z-20 flex items-center gap-3 px-4 py-3 bg-secondary border border-border dark:border-border rounded-xl shadow-lg">
      <span className="text-sm font-medium text-foreground mr-auto">
        {selectedCount} {selectedCount === 1 ? "trade" : "trades"} selected
      </span>

      <button
        type="button"
        onClick={onAssignPlaybook}
        className="px-3 py-1.5 bg-slate-200 dark:bg-slate-600 hover:bg-slate-500 text-foreground rounded-md text-sm transition-colors"
      >
        Assign Playbook
      </button>

      <button
        type="button"
        onClick={onAssignTag}
        className="px-3 py-1.5 bg-slate-200 dark:bg-slate-600 hover:bg-slate-500 text-foreground rounded-md text-sm transition-colors"
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
