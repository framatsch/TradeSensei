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
 * GenericImportCard — preview-then-confirm import of a Trade Sensei Execution
 * Format file (.json/.csv) into a GENERIC account.
 *
 * Selecting a file runs a read-only preview; the import is sent only after the
 * user confirms. Confirmation is disabled on validation errors or when the
 * file's ID strategy conflicts with the one recorded for the account.
 */

"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Spinner } from "@/components/ui/Spinner";
import {
  useGenericImportPreview,
  useGenericImportUpload,
  useGenericTemplateDownload,
} from "@/hooks/useGenericImport";
import type { GenericValidationIssue, ImportPreviewResult } from "@/lib/api/types.gen";

const STRATEGY_LABEL: Record<"external_id" | "fingerprint", string> = {
  external_id: "Broker fill IDs (external_id)",
  fingerprint: "Fingerprint (no fill IDs)",
};

const LINK_TEXT_CLASS = "text-[color-mix(in_srgb,var(--primary)_55%,var(--foreground))] hover:underline underline-offset-2 underline";
const DANGER_TEXT_CLASS = "text-[color-mix(in_srgb,var(--danger)_65%,var(--foreground))]";
const SUCCESS_TEXT_CLASS = "text-[color-mix(in_srgb,var(--success)_60%,var(--foreground))]";

interface Props {
  portfolioId: string;
  accountId: string;
}

export function GenericImportCard({ portfolioId, accountId }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const preview = useGenericImportPreview();
  const upload = useGenericImportUpload();
  const template = useGenericTemplateDownload();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    upload.reset();
    preview.reset();
    if (selected) preview.mutate({ portfolioId, accountId, file: selected });
  };

  const handleReset = () => {
    setFile(null);
    preview.reset();
    upload.reset();
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const previewResult = preview.data;
  const issues = preview.error?.issues ?? upload.error?.issues ?? [];
  const canConfirm = !!file && !!previewResult && !previewResult.strategy_conflict && !upload.isPending && !upload.isSuccess;

  return (
    <div className="solid-card p-6 space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">Upload Execution File</h3>
        <p className="text-xs text-muted-foreground">
          JSON or CSV in the Trade Sensei Execution Format. The file is checked first; nothing is imported until you confirm.
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          <Link href="/help#import-from-other-brokers" className={LINK_TEXT_CLASS}>
            Format help
          </Link>
          <button
            type="button"
            onClick={() => template.mutate()}
            disabled={template.isPending}
            className={`${LINK_TEXT_CLASS} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {template.isPending ? "Downloading…" : "Download CSV template"}
          </button>
        </div>
        {template.error && (
          <div role="alert" className="flex items-start gap-2 rounded-md border p-2.5 surface-danger">
            <AlertCircle size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${DANGER_TEXT_CLASS}`} />
            <p className={`text-xs ${DANGER_TEXT_CLASS}`}>{template.error.message}</p>
          </div>
        )}
      </div>

      {!upload.isSuccess && (
        <div className="space-y-1.5">
          <label htmlFor="generic-execution-file" className="block text-xs font-medium text-foreground">
            Execution file
          </label>
          <input
            id="generic-execution-file"
            ref={fileInputRef}
            type="file"
            accept=".json,.csv"
            onChange={handleFileChange}
            disabled={preview.isPending || upload.isPending}
            className="w-full text-muted-foreground text-sm disabled:opacity-50 disabled:cursor-not-allowed file:mr-4 file:py-2 file:px-4 file:rounded-md file:border file:border-solid file:border-[color-mix(in_srgb,var(--foreground)_28%,var(--border))] file:bg-secondary file:text-foreground file:cursor-pointer hover:file:bg-muted file:font-medium"
          />
        </div>
      )}

      {preview.isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner size="sm" /> Checking file…
        </div>
      )}

      {issues.length > 0 && <IssueList issues={issues} />}

      {(preview.error || upload.error) && issues.length === 0 && (
        <div role="alert" className="flex items-start gap-2 rounded-md border p-3 surface-danger">
          <AlertCircle size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${DANGER_TEXT_CLASS}`} />
          <p className={`text-sm ${DANGER_TEXT_CLASS}`}>
            {(preview.error ?? upload.error)?.message}
          </p>
        </div>
      )}

      {previewResult && !upload.isSuccess && <PreviewSummary result={previewResult} />}

      {upload.isSuccess ? (
        <div className="space-y-3">
          <div className="flex items-start gap-2 rounded-md border p-3 surface-success">
            <CheckCircle2 size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${SUCCESS_TEXT_CLASS}`} />
            <p role="status" className={`text-sm ${SUCCESS_TEXT_CLASS}`}>
              Imported {upload.data.raw_transactions_created} new execution{upload.data.raw_transactions_created === 1 ? "" : "s"}; {upload.data.trades_created} trade
              {upload.data.trades_created === 1 ? "" : "s"} created.
            </p>
          </div>
          {(upload.data.warnings ?? []).length > 0 && <WarningList warnings={upload.data.warnings ?? []} />}
          <button type="button" onClick={handleReset} className="btn-ghost px-4 py-2 rounded-md text-sm">
            Import another file
          </button>
        </div>
      ) : (
        file && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => upload.mutate({ portfolioId, accountId, file })}
              disabled={!canConfirm}
              className="btn-primary flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {upload.isPending && (
                <Spinner
                  size="sm"
                  className="border-[color-mix(in_srgb,var(--primary-foreground)_30%,transparent)] border-t-primary-foreground"
                />
              )}
              {upload.isPending ? "Importing…" : "Confirm import"}
            </button>
            <button
              type="button"
              onClick={handleReset}
              disabled={upload.isPending}
              className="btn-ghost px-4 py-2 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Choose another file
            </button>
          </div>
        )
      )}
    </div>
  );
}

function PreviewSummary({ result }: { result: ImportPreviewResult }) {
  const counts: Array<[string, number]> = [
    ["Executions in file", result.total ?? 0],
    ["New", result.new ?? 0],
    ["Already imported", result.already_imported ?? 0],
    ["Suppressed", result.suppressed ?? 0],
    ["New splits", result.new_splits ?? 0],
    ["Conflicting splits", result.conflicting_splits ?? 0],
  ];
  const detected = result.detected_strategy ? STRATEGY_LABEL[result.detected_strategy] : "—";
  const recorded = result.recorded_strategy ? STRATEGY_LABEL[result.recorded_strategy] : "Not set yet (set by the first import)";

  return (
    <div className="space-y-3" aria-label="Import preview">
      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
        {counts.map(([label, value]) => (
          <div key={label} className="rounded-md border border-border px-3 py-1.5 sm:py-2">
            <dt className="text-[11px] text-muted-foreground">{label}</dt>
            <dd className="font-mono text-sm text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
      <dl className="text-xs space-y-1">
        <div className="flex flex-wrap gap-x-2">
          <dt className="text-muted-foreground">ID strategy in file:</dt>
          <dd className="text-foreground">{detected}</dd>
        </div>
        <div className="flex flex-wrap gap-x-2">
          <dt className="text-muted-foreground">Recorded for account:</dt>
          <dd className="text-foreground">{recorded}</dd>
        </div>
      </dl>
      {result.strategy_conflict && (
        <div role="alert" className="flex items-start gap-2 rounded-md border p-3 surface-danger">
          <AlertCircle size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${DANGER_TEXT_CLASS}`} />
          <p className={`text-sm ${DANGER_TEXT_CLASS}`}>
            This file uses a different ID strategy than earlier imports into this account. Convert the file to the recorded strategy, import it into a
            separate account, or clear all trades of this account (Settings → Accounts) to reset the strategy.
          </p>
        </div>
      )}
      {(result.warnings ?? []).length > 0 && <WarningList warnings={result.warnings ?? []} />}
    </div>
  );
}

function IssueList({ issues }: { issues: GenericValidationIssue[] }) {
  return (
    <div role="alert" className="rounded-md border p-3 surface-danger space-y-1.5">
      <div className="flex items-start gap-2">
        <AlertCircle size={16} aria-hidden="true" className={`mt-0.5 shrink-0 ${DANGER_TEXT_CLASS}`} />
        <p className={`text-sm font-medium ${DANGER_TEXT_CLASS}`}>The file was rejected. Fix these issues and select it again:</p>
      </div>
      <ul className="text-xs text-foreground space-y-0.5 max-h-48 overflow-y-auto pl-6">
        {issues.map((issue, idx) => (
          <li key={`${issue.row}-${issue.field}-${issue.code}-${idx}`} className="font-mono">
            {issue.row === null || issue.row === undefined ? "File" : `Row ${issue.row}`} · {issue.field} · {issue.code}: {issue.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function WarningList({ warnings }: { warnings: string[] }) {
  return (
    <ul className="text-xs text-muted-foreground space-y-0.5">
      {warnings.map((warning, idx) => (
        <li key={`${idx}-${warning}`}>⚠ {warning}</li>
      ))}
    </ul>
  );
}
