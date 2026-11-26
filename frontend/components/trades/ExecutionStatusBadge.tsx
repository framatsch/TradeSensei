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
 * - No dark-mode prefix modifier — semantic CSS variable tokens only.
 * - Colors are achieved via Tailwind opacity utilities on semantic backgrounds.
 */

"use client";

import type { ExecutionOrigin } from "@/lib/types";

interface Props {
  origin: ExecutionOrigin;
  deleted?: boolean;
  user_modified?: boolean;
  parent_id?: string | null;
}

interface BadgeStyle {
  label: string;
  className: string;
}

function resolveBadge(
  origin: ExecutionOrigin,
  deleted: boolean,
  userModified: boolean,
  parentId: string | null
): BadgeStyle {
  if (deleted) {
    return {
      label: "Deleted",
      className: "bg-muted text-muted-foreground border border-border",
    };
  }
  if (origin === "imported" && userModified) {
    return {
      label: "Edited",
      className: "badge-caution",
    };
  }
  if (origin === "imported") {
    return {
      label: "Imported",
      className: "badge-neutral",
    };
  }
  if (origin === "manual") {
    return {
      label: "Manual",
      className: "badge-neutral",
    };
  }
  if (origin === "merged") {
    return {
      label: "Merged",
      className: "badge-neutral",
    };
  }
  // origin === "split"
  return {
    label: parentId ? "Split Child" : "Split",
    className: "badge-neutral",
  };
}

export function ExecutionStatusBadge({ origin, deleted = false, user_modified = false, parent_id = null }: Props) {
  const badge = resolveBadge(origin, deleted, user_modified, parent_id);

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${badge.className}`}
    >
      {badge.label}
    </span>
  );
}
