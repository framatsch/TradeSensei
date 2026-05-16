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
 * InsufficientDataBanner — displays a warning when a report requires fields
 * that are missing from some trades (e.g. Stop-Loss for R-Multiple analysis).
 *
 * The banner is dismissible for the current session via local state.
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import type { DataSufficiencyReport } from "@/lib/dataValidation";

interface InsufficientDataBannerProps {
  report: DataSufficiencyReport;
  /** Human-readable name of the analysis that requires the missing data. */
  analysisName: string;
  /** Optional href that pre-filters the Trades page to affected trades. */
  affectedTradesHref?: string;
  /** When true the banner is hidden entirely (e.g. coverage is 100%). */
  hidden?: boolean;
}

export function InsufficientDataBanner({
  report,
  analysisName,
  affectedTradesHref,
  hidden = false,
}: InsufficientDataBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (hidden || dismissed || report.invalidTrades === 0) return null;

  const plural = report.invalidTrades === 1 ? "trade is" : "trades are";
  const missingList = report.missingFieldSummary.join(", ");

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300"
    >
      {/* Warning icon */}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="mt-0.5 h-4 w-4 shrink-0"
        aria-hidden="true"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>

      <div className="flex-1 min-w-0">
        <p className="font-medium">
          Incomplete data for {analysisName}
        </p>
        <p className="mt-0.5 text-amber-600/90 dark:text-amber-400/90">
          {report.invalidTrades} {plural} missing:{" "}
          <span className="font-medium">{missingList}</span>.{" "}
          Only {report.coveragePercent}% of your trades ({report.validTrades}/
          {report.totalTrades}) are included in this analysis.
        </p>
        {affectedTradesHref && (
          <Link
            href={affectedTradesHref}
            className="mt-1.5 inline-block text-xs font-medium underline underline-offset-2 hover:no-underline"
          >
            View affected trades →
          </Link>
        )}
      </div>

      {/* Dismiss */}
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss warning"
        className="shrink-0 rounded p-0.5 hover:bg-amber-500/20 transition-colors"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
