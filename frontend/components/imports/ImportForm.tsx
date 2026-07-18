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
 * ImportForm — account-first import: API sync or multi-file upload.
 *
 * Step 1: Select account.
 * Step 2: Choose import method:
 *   - API Sync (IBKR/Schwab): with DateRangeVisualizer for Flex, days-picker for Schwab.
 *   - File Upload (all): multi-file selection, sequential queue with per-file progress.
 */

"use client";

import { useState, useRef, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAccounts, useUpdateAccount } from "@/hooks/useAccounts";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { Spinner } from "@/components/ui/Spinner";
import { FileQueue, FileQueueSummary } from "@/components/imports/FileQueue";
import { ImportDateRange } from "@/components/imports/ImportDateRange";
import { capabilityFor } from "@/components/imports/ImportCapability";
import type { QueuedFile } from "@/components/imports/FileQueue";
import type { ImportResult, BrokerSyncResult, ResponseEnvelope, AccountType, FlexFromDatePreset } from "@/lib/types";
import { client } from "@/lib/api/client.gen";
import { extractApiError } from "@/lib/apiErrors";

/** Multipart upload via raw fetch — bypasses the JSON body serializer of the SDK client. */
async function multipartPost(path: string, formData: FormData): Promise<any> {
  const token = localStorage.getItem("access_token");
  const baseUrl = client.getConfig().baseUrl ?? "";
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw err;
  }
  return res.json();
}

// Type badge helper
const TYPE_LABEL: Record<AccountType, string> = {
  manual: "Manual",
  schwab: "Schwab",
  ibkr: "IBKR",
};

// Accepted file extensions per account type
const ACCOUNT_ACCEPT: Record<AccountType, string> = {
  ibkr: ".xml",
  schwab: ".json",
  manual: "",
};

// Human-readable format hint per account type
const ACCOUNT_FORMAT_HINT: Record<AccountType, string> = {
  ibkr: "XML (IBKR Flex Query)",
  schwab: "JSON files (Schwab Transactions)",
  manual: "",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function getTodayYYYYMMDD(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

function getYTDFromDate(): string {
  const year = new Date().getFullYear();
  return `${year}0101`;
}

/** Compute the number of days between a YYYYMMDD start date and today. */
function computeDaysFromFromDate(fromDateStr: string): number {
  if (!/^\d{8}$/.test(fromDateStr)) return 30;
  const y = parseInt(fromDateStr.slice(0, 4), 10);
  const m = parseInt(fromDateStr.slice(4, 6), 10) - 1;
  const d = parseInt(fromDateStr.slice(6, 8), 10);
  const start = new Date(y, m, d);
  if (isNaN(start.getTime())) return 30;
  const msInDay = 86_400_000;
  return Math.max(1, Math.ceil((Date.now() - start.getTime()) / msInDay));
}

// ── Main component ────────────────────────────────────────────────────────────

export function ImportForm() {
  const qc = useQueryClient();
  const [accountId, setAccountId] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"sync" | "upload">("sync");

  // ── File-queue state ──
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isQueueRunning, setIsQueueRunning] = useState(false);
  const [queueDone, setQueueDone] = useState(false);
  const abortRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── API Sync state ──
  const [syncResult, setSyncResult] = useState<BrokerSyncResult | null>(null);

  // ── Overwrite manually-edited trades flag ──
  const [overwriteManuallyEdited, setOverwriteManuallyEdited] = useState(false);

  // ── Flex date-range state ──
  const [flexPreset, setFlexPreset] = useState<FlexFromDatePreset>("ytd");
  const [flexCustomDate, setFlexCustomDate] = useState<string>(getYTDFromDate());
  const [saveSettingsLabel, setSaveSettingsLabel] = useState<"save" | "saving" | "saved">("save");

  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  const { data: accounts, isLoading: loadingAccounts } = useAccounts(portfolioId ?? undefined);
  const updateAccount = useUpdateAccount(accountId);

  const selectedAccount = accounts?.find((a) => a.id === accountId) ?? null;
  const accountType: AccountType | null = selectedAccount?.type ?? null;

  // Pre-fill Flex settings from account settings when account changes
  const handleAccountChange = (id: string) => {
    setAccountId(id);
    setQueuedFiles([]);
    setQueueDone(false);
    setSyncResult(null);
    setOverwriteManuallyEdited(false);
    abortRef.current = false;

    const acc = accounts?.find((a) => a.id === id);
    // Default to sync tab when API keys exist, otherwise upload
    setActiveTab(acc?.has_api_keys ? "sync" : "upload");
    if (acc?.settings) {
      setFlexPreset(acc.settings.flex_from_date_preset ?? "ytd");
      setFlexCustomDate(acc.settings.flex_custom_from_date ?? getYTDFromDate());
    } else {
      setFlexPreset("ytd");
      setFlexCustomDate(getYTDFromDate());
    }
  };

  const getFlexFromDate = (): string => {
    if (flexPreset === "ytd") return getYTDFromDate();
    return flexCustomDate || getYTDFromDate();
  };

  // ── Save settings to account ──────────────────────────────────────────────
  const handleSaveSettings = async () => {
    if (!accountId) return;
    setSaveSettingsLabel("saving");
    await updateAccount.mutateAsync({
      settings: {
        sync_days: computeDaysFromFromDate(getFlexFromDate()),
        flex_from_date_preset: flexPreset,
        flex_custom_from_date: flexPreset === "custom" ? flexCustomDate : null,
      },
    });
    setSaveSettingsLabel("saved");
    setTimeout(() => setSaveSettingsLabel("save"), 2000);
  };

  // ── Sequential file upload queue ──────────────────────────────────────────
  const runQueue = useCallback(
    async (files: QueuedFile[], overwrite: boolean) => {
      setIsQueueRunning(true);
      abortRef.current = false;

      for (let i = 0; i < files.length; i++) {
        if (abortRef.current) break;

        setCurrentIndex(i);
        setQueuedFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "uploading" } : f))
        );

        const qf = files[i];
        try {
          const formData = new FormData();
          formData.append("account_id", accountId);
          formData.append("file", qf.file);
          if (overwrite) formData.append("overwrite_manually_edited", "true");

          const envelope = await multipartPost(`/api/v1/portfolios/${portfolioId}/imports/upload`, formData);
          const result = envelope.data;

          setQueuedFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: "done", result } : f
            )
          );
        } catch (err) {
          const errorMsg = extractApiError(err, err instanceof Error ? err.message : "Upload failed.");
          setQueuedFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, status: "error", error: errorMsg } : f
            )
          );
        }
      }

      setIsQueueRunning(false);
      setQueueDone(true);
      if (fileInputRef.current) fileInputRef.current.value = "";

      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["accounts"] });
    },
    [accountId, qc]
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    const queued: QueuedFile[] = files.map((f) => ({ file: f, status: "pending" }));
    setQueuedFiles(queued);
    setQueueDone(false);
    setCurrentIndex(0);
  };

  const handleStartUpload = () => {
    if (!queuedFiles.length || !accountType) return;
    runQueue(queuedFiles, overwriteManuallyEdited);
  };

  const handleAbort = () => {
    abortRef.current = true;
  };

  const handleReset = () => {
    setQueuedFiles([]);
    setQueueDone(false);
    setCurrentIndex(0);
    abortRef.current = false;
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── API Sync mutation ─────────────────────────────────────────────────────
  const {
    mutate: syncAccount,
    isPending: isSyncing,
    error: syncError,
  } = useMutation<BrokerSyncResult, Error, void>({
    mutationFn: async () => {
      const cap = selectedAccount ? capabilityFor(selectedAccount.type) : null;
      const fromDateStr = getFlexFromDate();
      const days = computeDaysFromFromDate(fromDateStr);
      const fromDateParam = cap?.syncParam.kind === "fromDate" ? `&from_date=${fromDateStr}` : "";
      const overwrite = overwriteManuallyEdited ? "&overwrite_manually_edited=true" : "";
      const { data: syncData, error: syncErr } = await client.post({ url: `/api/v1/broker/sync/${accountId}?days=${days}${fromDateParam}${overwrite}` as any });
      if (syncErr || !syncData) throw syncErr ?? new Error("Sync failed");
      return (syncData as any).data;
    },
    onSuccess: (data) => {
      setSyncResult(data);
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  const syncErrorMsg = (() => {
    if (!syncError) return null;
    return extractApiError(syncError, "Sync failed.");
  })();

  // ── Derived state ─────────────────────────────────────────────────────────
  const hasFiles = queuedFiles.length > 0;
  const allFilesDone = hasFiles && queuedFiles.every((f) => f.status === "done" || f.status === "error");
  const canStartUpload = hasFiles && !isQueueRunning && !allFilesDone;

  return (
    <div className="space-y-6">
      {/* Step 1: Account selection */}
      <div className="bg-card rounded-xl border border-border p-6 space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            Step 1 — Select Account
          </h2>
          <p className="text-xs text-muted-foreground dark:text-zinc-400 mt-0.5">
            Choose the trading account you want to import trades into.
          </p>
        </div>

        {loadingAccounts ? (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Spinner size="sm" /> Loading accounts…
          </div>
        ) : (
          <select
            value={accountId}
            onChange={(e) => handleAccountChange(e.target.value)}
            className="w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">— Select an account —</option>
            {(accounts ?? [])
              .filter((a) => a.is_active)
              .map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({TYPE_LABEL[acc.type]})
                </option>
              ))}
          </select>
        )}
      </div>

      {/* Step 2: Import options — tabs for sync / file upload */}
      {selectedAccount && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Step 2 — Import Trades
          </h2>

          {/* Tabs (only when both methods are available: broker + API keys) */}
          {(accountType === "schwab" || accountType === "ibkr") && selectedAccount.has_api_keys ? (
            <div className="space-y-4">
              <div className="flex gap-1 border-b border-border" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "sync"}
                  onClick={() => setActiveTab("sync")}
                  className={[
                    "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
                    activeTab === "sync"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  Sync via API
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "upload"}
                  onClick={() => setActiveTab("upload")}
                  className={[
                    "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
                    activeTab === "upload"
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  Upload Files
                </button>
              </div>

              {activeTab === "sync" ? (
                <div className="bg-card rounded-xl border border-border p-6 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      Sync via API
                    </h3>
                    <p className="text-xs text-muted-foreground dark:text-zinc-400 mt-0.5">
                      Fetch recent trades directly from {TYPE_LABEL[accountType]}.
                    </p>
                  </div>

                  {!syncResult && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">
                          Import date range
                        </p>
                      <ImportDateRange
                        capability={capabilityFor(selectedAccount.type)}
                        preset={flexPreset}
                        customFromDate={flexCustomDate}
                        onPresetChange={setFlexPreset}
                        onCustomFromDateChange={setFlexCustomDate}
                        disabled={isSyncing}
                      />
                      </div>

                      {/* Save settings button */}
                      <button
                        type="button"
                        onClick={handleSaveSettings}
                        disabled={isSyncing || saveSettingsLabel === "saving"}
                        className="text-xs text-primary hover:text-primary disabled:opacity-50 underline underline-offset-2"
                      >
                        {saveSettingsLabel === "saving"
                          ? "Saving…"
                          : saveSettingsLabel === "saved"
                          ? "✓ Saved as default"
                          : "Save as default for this account"}
                      </button>

                      {/* Overwrite manually-edited trades */}
                      <label className="flex gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={overwriteManuallyEdited}
                          onChange={(e) => setOverwriteManuallyEdited(e.target.checked)}
                          disabled={isSyncing}
                          className="w-4 h-4 rounded border-zinc-400 accent-amber-500"
                        />
                        <span className="text-xs text-muted-foreground dark:text-zinc-400">
                          Overwrite manually-edited trades
                        </span>
                      </label>
                    </div>
                  )}

                  {syncErrorMsg && (
                    <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
                      {syncErrorMsg}
                    </p>
                  )}

                  {syncResult ? (
                    <SyncResultPanel result={syncResult} onReset={() => setSyncResult(null)} />
                  ) : (
                    <button
                      type="button"
                      disabled={isSyncing}
                      onClick={() => syncAccount()}
                      className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
                    >
                      {isSyncing && <Spinner size="sm" />}
                      {isSyncing ? "Syncing…" : `Sync ${TYPE_LABEL[accountType]} Trades`}
                    </button>
                  )}
                </div>
              ) : (
                <FileUploadCard
                  accountType={accountType}
                  queuedFiles={queuedFiles}
                  currentIndex={currentIndex}
                  isQueueRunning={isQueueRunning}
                  queueDone={queueDone}
                  allFilesDone={allFilesDone}
                  canStartUpload={canStartUpload}
                  hasFiles={hasFiles}
                  overwriteManuallyEdited={overwriteManuallyEdited}
                  setOverwriteManuallyEdited={setOverwriteManuallyEdited}
                  fileInputRef={fileInputRef}
                  handleFileChange={handleFileChange}
                  handleStartUpload={handleStartUpload}
                  handleAbort={handleAbort}
                  handleReset={handleReset}
                />
              )}
            </div>
          ) : (accountType === "ibkr" || accountType === "schwab") ? (
            /* Broker account without API keys — only show upload */
            <div className="bg-card rounded-xl border border-border p-6 space-y-4">
              <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-md px-4 py-3">
                <span className="text-amber-600 dark:text-amber-400 text-sm leading-relaxed">
                  ⚠ No API credentials stored for this {TYPE_LABEL[accountType]} account. Add them in Settings → Accounts to enable API sync, or upload files below.
                </span>
              </div>
              <FileUploadCard
                accountType={accountType}
                queuedFiles={queuedFiles}
                currentIndex={currentIndex}
                isQueueRunning={isQueueRunning}
                queueDone={queueDone}
                allFilesDone={allFilesDone}
                canStartUpload={canStartUpload}
                hasFiles={hasFiles}
                overwriteManuallyEdited={overwriteManuallyEdited}
                setOverwriteManuallyEdited={setOverwriteManuallyEdited}
                fileInputRef={fileInputRef}
                handleFileChange={handleFileChange}
                handleStartUpload={handleStartUpload}
                handleAbort={handleAbort}
                handleReset={handleReset}
              />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────────

interface FileUploadCardProps {
  accountType: AccountType;
  queuedFiles: QueuedFile[];
  currentIndex: number;
  isQueueRunning: boolean;
  queueDone: boolean;
  allFilesDone: boolean;
  canStartUpload: boolean;
  hasFiles: boolean;
  overwriteManuallyEdited: boolean;
  setOverwriteManuallyEdited: (v: boolean) => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleStartUpload: () => void;
  handleAbort: () => void;
  handleReset: () => void;
}

function FileUploadCard({
  accountType,
  queuedFiles,
  currentIndex,
  isQueueRunning,
  queueDone,
  allFilesDone,
  canStartUpload,
  hasFiles,
  overwriteManuallyEdited,
  setOverwriteManuallyEdited,
  fileInputRef,
  handleFileChange,
  handleStartUpload,
  handleAbort,
  handleReset,
}: FileUploadCardProps) {
  return (
    <div className="bg-card rounded-xl border border-border p-6 space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">
          Upload Files
        </h3>
        <p className="text-xs text-muted-foreground dark:text-zinc-400 mt-0.5">
          Import from broker export files ({ACCOUNT_FORMAT_HINT[accountType]}).
        </p>
      </div>

      {/* File input — multi */}
      {!isQueueRunning && !queueDone && (
        <div className="space-y-2">
          <input
            ref={fileInputRef}
            id="file"
            type="file"
            multiple
            accept={ACCOUNT_ACCEPT[accountType]}
            onChange={handleFileChange}
            className="w-full text-muted-foreground text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-secondary file:text-foreground file:cursor-pointer hover:file:bg-zinc-200 dark:hover:file:bg-zinc-700 file:font-medium"
          />
          {hasFiles && (
            <p className="text-xs text-muted-foreground dark:text-zinc-400">
              {queuedFiles.length} file{queuedFiles.length !== 1 ? "s" : ""} selected
            </p>
          )}
        </div>
      )}

      {/* Queue progress (while running) */}
      {(isQueueRunning || (hasFiles && !queueDone)) && !allFilesDone && (
        <FileQueue files={queuedFiles} currentIndex={currentIndex} />
      )}

      {/* Running: abort button */}
      {isQueueRunning && (
        <button
          type="button"
          onClick={handleAbort}
          className="text-xs text-red-400 hover:text-red-300 underline"
        >
          Cancel remaining files
        </button>
      )}

      {/* Done: summary + reset */}
      {queueDone && (
        <div className="space-y-3">
          <FileQueue files={queuedFiles} currentIndex={currentIndex} />
          <FileQueueSummary files={queuedFiles} />
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-muted-foreground hover:text-zinc-700 dark:hover:text-zinc-300 underline"
          >
            Import more files
          </button>
        </div>
      )}

      {/* Start button */}
      {canStartUpload && (
        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={overwriteManuallyEdited}
              onChange={(e) => setOverwriteManuallyEdited(e.target.checked)}
              className="w-4 h-4 rounded border-zinc-400 accent-amber-500"
            />
            <span className="text-xs text-muted-foreground dark:text-zinc-400">
              Overwrite manually-edited trades
            </span>
          </label>
          <button
            type="button"
            onClick={handleStartUpload}
            className="flex items-center gap-2 px-5 py-2.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
          >
            Import {queuedFiles.length} file{queuedFiles.length !== 1 ? "s" : ""}
          </button>
        </div>
      )}
    </div>
  );
}

function SyncResultPanel({
  result,
  onReset,
}: {
  result: BrokerSyncResult;
  onReset: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-4">
        <StatBox label="Imported" value={result.imported_count} color="text-emerald-400" />
        <StatBox label="Skipped" value={result.skipped_count} color="text-amber-400" />
        <StatBox label="Errors" value={result.errors.length} color="text-red-400" />
      </div>
      {result.errors.length > 0 && (
        <ul className="space-y-1 max-h-32 overflow-y-auto">
          {result.errors.map((e, i) => (
            <li key={i} className="text-xs text-red-400 bg-red-900/10 px-3 py-1.5 rounded">
              {e}
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={onReset}
        className="text-xs text-muted-foreground hover:text-zinc-700 dark:hover:text-zinc-300 underline"
      >
        Sync again
      </button>
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

// Helper referenced in handleAccountChange — alias kept for compatibility
