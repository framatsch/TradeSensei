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
 * FileQueue — displays a list of queued files with per-file upload status.
 *
 * Each entry shows a status icon, filename, file size, and either a
 * result summary (trades created/skipped) or an error message once
 * processing is complete.
 */

"use client";

import type { ImportResult } from "@/lib/types";

export type FileStatus = "pending" | "uploading" | "done" | "error";

export interface QueuedFile {
  file: File;
  status: FileStatus;
  result?: ImportResult;
  error?: string;
}

interface FileQueueProps {
  files: QueuedFile[];
  currentIndex: number;
}

const STATUS_ICON: Record<FileStatus, React.ReactNode> = {
  pending: (
    <span className="w-5 h-5 rounded-full border-2 border-zinc-400 dark:border-border flex-shrink-0" />
  ),
  uploading: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
      <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
    </span>
  ),
  done: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
      ✓
    </span>
  ),
  error: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full bg-red-500/20 text-red-400 text-xs font-bold">
      ✗
    </span>
  ),
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileQueue({ files, currentIndex }: FileQueueProps) {
  const done = files.filter((f) => f.status === "done" || f.status === "error").length;
  const total = files.length;
  const progressPct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="space-y-3">
      {/* Overall progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground dark:text-zinc-400">
          <span>
            {done < total
              ? `Processing file ${Math.min(currentIndex + 1, total)} of ${total}…`
              : `All ${total} files processed`}
          </span>
          <span>{progressPct}%</span>
        </div>
        <div className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Per-file list */}
      <ul className="space-y-1.5">
        {files.map((qf, idx) => (
          <li
            key={idx}
            className={[
              "flex items-start gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
              qf.status === "uploading"
                ? "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
                : qf.status === "done"
                ? "bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-900"
                : qf.status === "error"
                ? "bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900"
                : "bg-zinc-50 dark:bg-zinc-800/50 border border-border",
            ].join(" ")}
          >
            <div className="mt-0.5">{STATUS_ICON[qf.status]}</div>

            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground truncate">
                {qf.file.name}
              </p>
              <p className="text-xs text-muted-foreground dark:text-zinc-400">
                {formatBytes(qf.file.size)}
              </p>

              {/* Result summary */}
              {qf.status === "done" && qf.result && (
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs">
                  <span className="text-emerald-600 dark:text-emerald-400">
                    +{qf.result.trades_created} created
                  </span>
                  {qf.result.trades_skipped > 0 && (
                    <span className="text-amber-600 dark:text-amber-400">
                      {qf.result.trades_skipped} skipped
                    </span>
                  )}
                  {qf.result.cash_transactions_created > 0 && (
                    <span className="text-primary dark:text-primary">
                      +{qf.result.cash_transactions_created} cash txns
                    </span>
                  )}
                  {qf.result.warnings.length > 0 && (
                    <span className="text-orange-500 dark:text-orange-400">
                      {qf.result.warnings.length} warning{qf.result.warnings.length !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              )}

              {/* Error message */}
              {qf.status === "error" && qf.error && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{qf.error}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Aggregate summary shown after all files are processed ─────────────────────

export function FileQueueSummary({ files }: { files: QueuedFile[] }) {
  const totalCreated = files.reduce((s, f) => s + (f.result?.trades_created ?? 0), 0);
  const totalSkipped = files.reduce((s, f) => s + (f.result?.trades_skipped ?? 0), 0);
  const totalCash = files.reduce(
    (s, f) => s + (f.result?.cash_transactions_created ?? 0),
    0
  );
  const errorCount = files.filter((f) => f.status === "error").length;
  const warnCount = files.reduce((s, f) => s + (f.result?.warnings.length ?? 0), 0);

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      <p className="text-sm font-semibold text-foreground">
        Import complete — {files.length} file{files.length !== 1 ? "s" : ""} processed
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryBox label="Trades Created" value={totalCreated} color="text-emerald-500" />
        <SummaryBox label="Trades Skipped" value={totalSkipped} color="text-amber-500" />
        <SummaryBox label="Cash Txns" value={totalCash} color="text-primary" />
        <SummaryBox
          label="Files with Errors"
          value={errorCount}
          color={errorCount > 0 ? "text-red-500" : "text-zinc-400"}
        />
      </div>
      {warnCount > 0 && (
        <p className="text-xs text-orange-500 dark:text-orange-400">
          {warnCount} warning{warnCount !== 1 ? "s" : ""} across all files — expand individual files for details.
        </p>
      )}
    </div>
  );
}

function SummaryBox({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="text-center bg-zinc-50 dark:bg-zinc-700/50 rounded-lg py-2 px-1">
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-muted-foreground dark:text-zinc-400 mt-0.5">{label}</p>
    </div>
  );
}
