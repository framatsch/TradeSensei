/**
 * ExecutionStatusBadge — colored badge for execution status.
 * imported = blue, manual = purple, merged = orange, split = cyan
 */

"use client";

import type { ExecutionStatus } from "@/lib/types";

interface Props {
  status: ExecutionStatus;
}

const STATUS_STYLES: Record<ExecutionStatus, string> = {
  imported:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800",
  manual:
    "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400 border border-purple-200 dark:border-purple-800",
  merged:
    "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400 border border-orange-200 dark:border-orange-800",
  split:
    "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800",
};

export function ExecutionStatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}
