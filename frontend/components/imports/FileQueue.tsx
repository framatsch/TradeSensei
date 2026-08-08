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

import { useState } from "react";
import { Copy, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";
import type { ImportResult } from "@/lib/types";
import { ImportLogLine } from "@/components/imports/ImportLogLine";

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
    <span className="w-5 h-5 rounded-full border-2 border-border flex-shrink-0" />
  ),
  uploading: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
      <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
    </span>
  ),
  done: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--success)_20%,transparent)] text-success text-xs font-bold">
      ✓
    </span>
  ),
  error: (
    <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full bg-[color-mix(in_srgb,var(--danger)_20%,transparent)] text-danger text-xs font-bold">
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
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {done < total
              ? `Processing file ${Math.min(currentIndex + 1, total)} of ${total}…`
              : `All ${total} files processed`}
          </span>
          <span>{progressPct}%</span>
        </div>
        <div className="w-full h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Per-file list */}
      <ul className="space-y-1.5">
        {files.map((qf, idx) => (
          <FileQueueItem key={idx} qf={qf} />
        ))}
      </ul>
    </div>
  );
}

// ── Aggregate summary shown after all files are processed ─────────────────────

export function FileQueueSummary({ files }: { files: QueuedFile[] }) {
  const totalCreated = files.reduce((s, f) => s + (f.result?.trades_created ?? 0), 0);
  const totalSkipped = files.reduce((s, f) => s + (f.result?.trades_skipped ?? 0), 0);
  const totalProtected = files.reduce((s, f) => s + (f.result?.trades_protected_reconciled ?? 0), 0);
  const errorCount = files.filter((f) => f.status === "error").length;
  const warnCount = files.reduce((s, f) => s + (f.result?.warnings.length ?? 0), 0);

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      <p className="text-sm font-semibold text-foreground">
        Import complete — {files.length} file{files.length !== 1 ? "s" : ""} processed
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryBox label="Created" value={totalCreated} color="text-success" />
        <SummaryBox label="Skipped" value={totalSkipped} color="text-warning" />
        <SummaryBox label="Protected" value={totalProtected} color="text-primary" />
        <SummaryBox
          label="Errors"
          value={errorCount}
          color={errorCount > 0 ? "text-danger" : "text-muted-foreground"}
        />
      </div>
      {warnCount > 0 && (
        <p className="text-xs text-warning">
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
    <div className="text-center bg-[color-mix(in_srgb,var(--muted)_40%,transparent)] rounded-lg py-2 px-1">
      <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}

function FileQueueItem({ qf }: { qf: QueuedFile }) {
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const logsPanelId = `file-queue-logs-${qf.file.name}`;

  const activityLog = qf.result?.activity_log ?? [];
  const warnings = qf.result?.warnings ?? [];
  const logLines = [...activityLog, ...warnings];
  const hasWarnings = warnings.length > 0;
  // Show the Logs panel whenever there's anything to show — not just when new
  // trades were created. A purely-reconciled import (onto protected trades) has
  // zero new trades but may still have activity/warnings worth reviewing.
  const shouldShowLogs = logLines.length > 0;
  const protectedCount = qf.result?.trades_protected_reconciled ?? 0;

  const handleCopyLogs = () => {
    if (logLines.length === 0) return;
    const logText = logLines.map((w) => {
        const isProtected = w.startsWith("protected_");
        return isProtected ? `[INFO/PROTECTED] ${w}` : `[WARNING] ${w}`;
    }).join('\n');
    navigator.clipboard.writeText(logText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <li
      className={[
        "flex flex-col gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
        qf.status === "uploading"
          ? "bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] border-[color-mix(in_srgb,var(--primary)_20%,transparent)]"
          : qf.status === "done"
          ? "bg-[color-mix(in_srgb,var(--success)_10%,transparent)] border-[color-mix(in_srgb,var(--success)_20%,transparent)]"
          : qf.status === "error"
          ? "bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] border-[color-mix(in_srgb,var(--danger)_20%,transparent)]"
          : "bg-secondary border-border",
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{STATUS_ICON[qf.status]}</div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <div>
              <p className="font-medium text-foreground truncate">{qf.file.name}</p>
              <p className="text-xs text-muted-foreground">{formatBytes(qf.file.size)}</p>
            </div>
            {shouldShowLogs && (
              <button
                onClick={() => setIsLogsOpen(!isLogsOpen)}
                aria-expanded={isLogsOpen}
                aria-controls={logsPanelId}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 bg-[color-mix(in_srgb,var(--foreground)_8%,transparent)] px-2 py-1 rounded transition-colors"
              >
                Logs {isLogsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            )}
          </div>

          {/* Result summary */}
          {qf.status === "done" && qf.result && (
            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs">
              <span className="text-success">+{qf.result.trades_created} created</span>
              {qf.result.trades_skipped > 0 && (
                <span className="text-warning">{qf.result.trades_skipped} skipped</span>
              )}
              {protectedCount > 0 && (
                <span className="text-primary">{protectedCount} protected</span>
              )}
              {hasWarnings && (
                <span className="text-warning">
                  {warnings.length} warning{warnings.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}

          {/* Error message */}
          {qf.status === "error" && qf.error && (
            <p className="mt-1 text-xs text-danger">{qf.error}</p>
          )}
        </div>
      </div>
      
      {/* Expandable Logs */}
      {isLogsOpen && shouldShowLogs && (
        <div id={logsPanelId} className="relative mt-2 border border-border p-3 rounded bg-[color-mix(in_srgb,var(--foreground)_5%,transparent)]">
          <button
            onClick={handleCopyLogs}
            className="absolute top-2 right-2 p-1.5 rounded-md bg-secondary/80 hover:bg-secondary text-muted-foreground hover:text-foreground transition-all flex items-center gap-1 text-[10px]"
            title="Copy to clipboard"
          >
            {copied ? <CheckCircle2 size={12} className="text-success" /> : <Copy size={12} />}
            <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
          </button>
          <div className="space-y-1.5 font-mono text-[10px] max-h-48 overflow-y-auto pr-8 custom-scrollbar">
            {logLines.map((w, i) => (
              <ImportLogLine key={i} text={w} />
            ))}
          </div>
        </div>
      )}
    </li>
  );
}
