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
 * ConflictBanner — amber warning banner shown when a trade has a position conflict.
 * Dismissible for the current session only (useState).
 */

"use client";

import { useState } from "react";

interface Props {
  /** Optional callback when the user clicks the "Review executions" link. */
  onReview?: () => void;
}

export function ConflictBanner({ onReview }: Props) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="flex items-start gap-3 rounded-xl px-4 py-3.5 border bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
      {/* Warning icon */}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
          Position Conflict
        </p>
        <p className="mt-0.5 text-xs text-amber-700 dark:text-amber-400">
          The execution legs for this trade don&apos;t add up to a consistent position. Review the
          execution legs below to find and correct any mismatches.
          {onReview && (
            <>
              {" "}
              <button
                type="button"
                onClick={onReview}
                className="underline underline-offset-2 hover:opacity-80 transition-opacity font-medium"
              >
                Review executions
              </button>
            </>
          )}
        </p>
      </div>

      {/* Dismiss */}
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss conflict warning"
        className="p-0.5 rounded text-amber-600 dark:text-amber-400 hover:opacity-70 transition-opacity flex-shrink-0"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className="w-4 h-4"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
