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
import { DateRangeVisualizer } from "@/components/imports/DateRangeVisualizer";
import type { QueuedFile } from "@/components/imports/FileQueue";
import type { ImportResult, FreshStartResult, BrokerSyncResult, ResponseEnvelope, AccountType, FlexFromDatePreset } from "@/lib/types";
import { client } from "@/lib/api/client.gen";
import { extractApiError } from "@/lib/api/errors";

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

// ── Main component ────────────────────────────────────────────────────────────

export function ImportForm() {
  const qc = useQueryClient();
  const [accountId, setAccountId] = useState<string>("");
  const [showFileUpload, setShowFileUpload] = useState(false);

  // ── File-queue state ──
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isQueueRunning, setIsQueueRunning] = useState(false);
  const [queueDone, setQueueDone] = useState(false);
  const abortRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── API Sync state ──
  const [syncResult, setSyncResult] = useState<BrokerSyncResult | null>(null);
  const [syncDays, setSyncDays] = useState<number>(30);

  // ── Overwrite manually-edited trades flag ──
  const [overwriteManuallyEdited, setOverwriteManuallyEdited] = useState(false);

  // ── Fresh Start state (task 8.6) ──
  const [showFreshStart, setShowFreshStart] = useState(false);
  const [freshStartAcknowledged, setFreshStartAcknowledged] = useState(false);
  const [freshStartFile, setFreshStartFile] = useState<File | null>(null);
  const [freshStartResult, setFreshStartResult] = useState<FreshStartResult | null>(null);
  const [freshStartError, setFreshStartError] = useState<string | null>(null);
  const [isFreshStartRunning, setIsFreshStartRunning] = useState(false);
  const freshStartFileRef = useRef<HTMLInputElement>(null);

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
    setShowFileUpload(false);
    setOverwriteManuallyEdited(false);
    setShowFreshStart(false);
    setFreshStartAcknowledged(false);
    setFreshStartFile(null);
    setFreshStartResult(null);
    setFreshStartError(null);
    abortRef.current = false;

    const acc = accounts?.find((a) => a.id === id);
    if (acc?.settings) {
      setSyncDays(acc.settings.sync_days ?? 30);
      setFlexPreset(acc.settings.flex_from_date_preset ?? "ytd");
      setFlexCustomDate(acc.settings.flex_custom_from_date ?? getYTDFromDate());
    } else {
      setSyncDays(30);
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
        sync_days: syncDays,
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

  // ── Fresh Start handler (task 8.6) ───────────────────────────────────────
  const handleFreshStart = async () => {
    if (!freshStartFile || !accountType || !accountId || !freshStartAcknowledged) return;
    setIsFreshStartRunning(true);
    setFreshStartError(null);
    setFreshStartResult(null);

    try {
      const formData = new FormData();
      formData.append("acknowledged", "true");
      formData.append("file", freshStartFile);

      const freshEnvelope = await multipartPost(`/api/v1/portfolios/${portfolioId}/imports/${accountId}/fresh-start`, formData);
      setFreshStartResult(freshEnvelope.data);
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["accounts"] });
    } catch (err) {
      setFreshStartError(extractApiError(err, err instanceof Error ? err.message : "Fresh start failed."));
    } finally {
      setIsFreshStartRunning(false);
    }
  };

  // ── API Sync mutation ─────────────────────────────────────────────────────
  const {
    mutate: syncAccount,
    isPending: isSyncing,
    error: syncError,
  } = useMutation<BrokerSyncResult, Error, void>({
    mutationFn: async () => {
      const fromDate = accountType === "ibkr" ? `&from_date=${getFlexFromDate()}` : "";
      const overwrite = overwriteManuallyEdited ? "&overwrite_manually_edited=true" : "";
      const { data: syncData, error: syncErr } = await client.post({ url: `/api/v1/broker/sync/${accountId}?days=${syncDays}${fromDate}${overwrite}` as any });
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

      {/* Step 2: Import options */}
      {selectedAccount && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Step 2 — Import Trades
          </h2>

          {/* API Sync — only for ibkr/schwab */}
          {(accountType === "schwab" || accountType === "ibkr") && (
            <div className="bg-card rounded-xl border border-border p-6 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Sync via API
                </h3>
                <p className="text-xs text-muted-foreground dark:text-zinc-400 mt-0.5">
                  Fetch recent trades directly from {TYPE_LABEL[accountType]}.
                  {!selectedAccount.has_api_keys && (
                    <span className="text-amber-400 ml-1">
                      ⚠ No API credentials stored. Add them in Settings → Accounts.
                    </span>
                  )}
                </p>
              </div>

              {selectedAccount.has_api_keys && !syncResult && (
                <div className="space-y-4">
                  {/* IBKR Flex: DateRangeVisualizer */}
                  {accountType === "ibkr" ? (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        Import date range
                      </p>
                      <DateRangeVisualizer
                        preset={flexPreset}
                        customFromDate={flexCustomDate}
                        onPresetChange={setFlexPreset}
                        onCustomFromDateChange={setFlexCustomDate}
                        disabled={isSyncing}
                      />
                    </div>
                  ) : (
                    // Schwab: simple days picker
                    <div className="flex items-center gap-3">
                      <label className="text-xs font-medium text-muted-foreground">
                        Look back
                      </label>
                      <select
                        value={syncDays}
                        onChange={(e) => setSyncDays(Number(e.target.value))}
                        disabled={isSyncing}
                        className="px-2 py-1.5 bg-zinc-50 dark:bg-zinc-700 border border-border dark:border-border rounded text-sm text-zinc-700 dark:text-zinc-200 focus:outline-none focus:border-primary"
                      >
                        <option value={7}>Last 7 days</option>
                        <option value={30}>Last 30 days</option>
                        <option value={90}>Last 90 days</option>
                        <option value={180}>Last 180 days</option>
                        <option value={365}>Last 1 year</option>
                      </select>
                    </div>
                  )}

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
                  <label className="flex items-center gap-2 cursor-pointer select-none">
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
                  disabled={isSyncing || !selectedAccount.has_api_keys}
                  onClick={() => syncAccount()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
                >
                  {isSyncing && <Spinner size="sm" />}
                  {isSyncing ? "Syncing…" : `Sync ${TYPE_LABEL[accountType]} Trades`}
                </button>
              )}
            </div>
          )}

          {/* Fresh Start (task 8.6) — only for ibkr/schwab accounts */}
          {(accountType === "schwab" || accountType === "ibkr") && (
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <button
                type="button"
                onClick={() => setShowFreshStart((v) => !v)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-muted/30 transition-colors"
              >
                <span className="text-sm font-medium text-red-600">
                  Fresh Start (destructive)
                </span>
                <span className="text-muted-foreground text-xs">
                  {showFreshStart ? "▲ Hide" : "▼ Show"}
                </span>
              </button>

              {showFreshStart && (
                <div className="px-6 py-4 space-y-4 border-t border-border">
                  <p className="text-xs text-muted-foreground">
                    Deletes <strong>all</strong> trades and executions for this account, then re-imports
                    from the selected file. BrokerRawTransactions and suppressed records are preserved.
                    <br />
                    <strong className="text-red-600">This action cannot be undone.</strong>
                  </p>

                  {/* File input */}
                  {!freshStartResult && (
                    <>
                      <input
                        ref={freshStartFileRef}
                        type="file"
                        accept={accountType ? ACCOUNT_ACCEPT[accountType] : ""}
                        onChange={(e) => setFreshStartFile(e.target.files?.[0] ?? null)}
                        className="w-full text-muted-foreground text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-muted file:text-foreground file:cursor-pointer file:font-medium"
                      />

                      {/* Acknowledgement checkbox */}
                      <label className="flex items-start gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={freshStartAcknowledged}
                          onChange={(e) => setFreshStartAcknowledged(e.target.checked)}
                          disabled={isFreshStartRunning}
                          className="mt-0.5 w-4 h-4 rounded border-border accent-red-600 flex-shrink-0"
                        />
                        <span className="text-xs text-muted-foreground">
                          I understand that all trades and executions for this account will be
                          permanently deleted before the re-import.
                        </span>
                      </label>

                      {freshStartError && (
                        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                          {freshStartError}
                        </p>
                      )}

                      <button
                        type="button"
                        onClick={handleFreshStart}
                        disabled={!freshStartFile || !freshStartAcknowledged || isFreshStartRunning}
                        className="flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
                      >
                        {isFreshStartRunning ? (
                          <>
                            <Spinner size="sm" />
                            Running Fresh Start…
                          </>
                        ) : (
                          "Run Fresh Start"
                        )}
                      </button>
                    </>
                  )}

                  {freshStartResult && (
                    <div className="space-y-3">
                      <div className="grid grid-cols-3 gap-4">
                        <StatBox label="Deleted exec." value={freshStartResult.executions_deleted} color="text-red-500" />
                        <StatBox label="Deleted trades" value={freshStartResult.trades_deleted} color="text-red-500" />
                        <StatBox label="Imported" value={freshStartResult.import_result.trades_created} color="text-emerald-500" />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Fresh start complete. {freshStartResult.import_result.trades_skipped} rows skipped.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setFreshStartResult(null);
                          setFreshStartAcknowledged(false);
                          setFreshStartFile(null);
                          if (freshStartFileRef.current) freshStartFileRef.current.value = "";
                        }}
                        className="text-xs text-muted-foreground hover:text-foreground underline"
                      >
                        Run again
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* File Upload — only for broker accounts (ibkr/schwab) */}
          {(accountType === "ibkr" || accountType === "schwab") && (
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <button
                type="button"
                onClick={() => setShowFileUpload((v) => !v)}
                disabled={isQueueRunning}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-zinc-50 dark:hover:bg-zinc-700/50 transition-colors disabled:opacity-50"
              >
                <span className="text-sm font-medium text-muted-foreground">
                  Or upload files manually
                  <span className="ml-2 text-xs text-muted-foreground font-normal">
                    ({accountType ? ACCOUNT_FORMAT_HINT[accountType] : ""})
                  </span>
                </span>
                <span className="text-muted-foreground text-xs">
                  {showFileUpload ? "▲ Hide" : "▼ Show"}
                </span>
              </button>

              {showFileUpload && (
                <div className="px-6 py-4 space-y-4 border-t border-border">
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
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────────

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
