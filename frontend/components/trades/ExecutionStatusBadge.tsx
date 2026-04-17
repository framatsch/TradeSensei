/**
 * ExecutionStatusBadge — colored badge derived from execution origin, deleted, and
 * user_modified flags per the simplified-execution-model spec (task 8.3).
 *
 * Badge table:
 *   deleted=true                              → gray,   "Deleted"
 *   origin='imported' + user_modified=true   → amber,  "Edited"
 *   origin='imported' + user_modified=false  → blue,   "Imported"
 *   origin='manual'                           → violet, "Manual"
 *   origin='merged'                           → orange, "Merged"
 *   origin='split'                            → cyan,   "Split"
 *
 * Design rules:
 * - No `dark:` modifier — semantic CSS variable tokens only.
 * - Colors are achieved via Tailwind opacity utilities on semantic backgrounds.
 */

"use client";

import type { ExecutionOrigin } from "@/lib/types";

interface Props {
  origin: ExecutionOrigin;
  deleted?: boolean;
  user_modified?: boolean;
}

interface BadgeStyle {
  label: string;
  className: string;
}

function resolveBadge(origin: ExecutionOrigin, deleted: boolean, userModified: boolean): BadgeStyle {
  if (deleted) {
    return {
      label: "Deleted",
      className: "bg-muted text-muted-foreground border border-border",
    };
  }
  if (origin === "imported" && userModified) {
    return {
      label: "Edited",
      className: "bg-amber-100 text-amber-700 border border-amber-200",
    };
  }
  if (origin === "imported") {
    return {
      label: "Imported",
      className: "bg-blue-100 text-blue-700 border border-blue-200",
    };
  }
  if (origin === "manual") {
    return {
      label: "Manual",
      className: "bg-violet-100 text-violet-700 border border-violet-200",
    };
  }
  if (origin === "merged") {
    return {
      label: "Merged",
      className: "bg-orange-100 text-orange-700 border border-orange-200",
    };
  }
  // origin === "split"
  return {
    label: "Split",
    className: "bg-cyan-100 text-cyan-700 border border-cyan-200",
  };
}

export function ExecutionStatusBadge({ origin, deleted = false, user_modified = false }: Props) {
  const badge = resolveBadge(origin, deleted, user_modified);

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${badge.className}`}
    >
      {badge.label}
    </span>
  );
}
