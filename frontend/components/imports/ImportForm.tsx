/**
 * ImportForm — account-first import: API sync or file upload based on account type.
 */

"use client";

import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { useAccounts } from "@/hooks/useAccounts";
import { Spinner } from "@/components/ui/Spinner";
import type { ImportResult, BrokerSyncResult, ResponseEnvelope, AccountType } from "@/lib/types";
import type { AxiosError } from "axios";

// Type badge helper
const TYPE_LABEL: Record<AccountType, string> = {
  manual: "Manual",
  schwab: "Schwab",
  ibkr: "IBKR",
};

export function ImportForm() {
  const [accountId, setAccountId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadResult, setUploadResult] = useState<ImportResult | null>(null);
  const [syncResult, setSyncResult] = useState<BrokerSyncResult | null>(null);
  const [syncDays, setSyncDays] = useState<number>(30);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: accounts, isLoading: loadingAccounts } = useAccounts();

  const selectedAccount = accounts?.find((a) => a.id === accountId) ?? null;
  const accountType: AccountType | null = selectedAccount?.type ?? null;

  // File upload mutation
  const {
    mutate: uploadFile,
    isPending: isUploading,
    error: uploadError,
  } = useMutation<ImportResult, Error, void>({
    mutationFn: async () => {
      if (!file) throw new Error("No file selected.");
      const formData = new FormData();
      // Infer broker from account type for the backend parser
      if (accountType === "schwab") formData.append("broker", "schwab");
      else formData.append("broker", "ibkr");
      formData.append("account_id", accountId);
      formData.append("file", file);
      const res = await apiClient.post<ResponseEnvelope<ImportResult>>(
        "/api/v1/imports/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      setUploadResult(data);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
  });

  // API sync mutation
  const {
    mutate: syncAccount,
    isPending: isSyncing,
    error: syncError,
  } = useMutation<BrokerSyncResult, Error, void>({
    mutationFn: async () => {
      const res = await apiClient.post<ResponseEnvelope<BrokerSyncResult>>(
        `/api/v1/broker/sync/${accountId}?days=${syncDays}`
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      setSyncResult(data);
    },
  });

  const uploadErrorMsg = (() => {
    if (!uploadError) return null;
    const e = uploadError as AxiosError<{ detail?: string }>;
    return e.response?.data?.detail ?? "Import failed.";
  })();

  const syncErrorMsg = (() => {
    if (!syncError) return null;
    const e = syncError as AxiosError<{ detail?: string }>;
    return e.response?.data?.detail ?? "Sync failed.";
  })();

  return (
    <div className="space-y-6">
      {/* Step 1: Account selection */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Step 1 — Select Account
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Choose the trading account you want to import trades into.
          </p>
        </div>

        {loadingAccounts ? (
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <Spinner size="sm" /> Loading accounts…
          </div>
        ) : (
          <select
            value={accountId}
            onChange={(e) => {
              setAccountId(e.target.value);
              setFile(null);
              setUploadResult(null);
              setSyncResult(null);
              setShowFileUpload(false);
            }}
            className="w-full px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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

      {/* Step 2: Import options — shown only after account selected */}
      {selectedAccount && (
        <div className="space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Step 2 — Import Trades
            </h2>
          </div>

          {/* API Sync option — only for schwab/ibkr accounts */}
          {(accountType === "schwab" || accountType === "ibkr") && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Sync via API
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Fetch recent trades directly from{" "}
                    {TYPE_LABEL[accountType]}.
                    {!selectedAccount.has_api_keys && (
                      <span className="text-amber-400 ml-1">
                        ⚠ No API credentials stored. Add them in Settings → Accounts.
                      </span>
                    )}
                  </p>
                </div>
                {selectedAccount.has_api_keys && !syncResult && (
                  <select
                    value={syncDays}
                    onChange={(e) => setSyncDays(Number(e.target.value))}
                    disabled={isSyncing}
                    className="ml-4 px-2 py-1.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value={7}>Last 7 Days</option>
                    <option value={30}>Last 30 Days</option>
                    <option value={90}>Last 90 Days</option>
                    <option value={180}>Last 180 Days</option>
                    <option value={365}>Last 1 Year</option>
                  </select>
                )}
              </div>

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
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
                >
                  {isSyncing && <Spinner size="sm" />}
                  {isSyncing ? "Syncing…" : `Sync ${TYPE_LABEL[accountType]} Trades`}
                </button>
              )}
            </div>
          )}

          {/* File Upload */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {/* Collapsible header for API accounts */}
            {accountType !== "manual" ? (
              <button
                type="button"
                onClick={() => setShowFileUpload((v) => !v)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Or upload a file manually
                </span>
                <span className="text-slate-500 text-xs">
                  {showFileUpload ? "▲ Hide" : "▼ Show"}
                </span>
              </button>
            ) : (
              <div className="px-6 pt-5 pb-0">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Upload Trade File
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Supported: CSV, XLSX, XML</p>
              </div>
            )}

            {(accountType === "manual" || showFileUpload) && (
              <div className="px-6 py-4 space-y-4">
                <input
                  ref={fileInputRef}
                  id="file"
                  type="file"
                  accept=".csv,.xlsx,.xls,.xml"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="w-full text-slate-700 dark:text-slate-300 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-slate-600 file:text-white file:cursor-pointer hover:file:bg-slate-500"
                />

                {uploadErrorMsg && (
                  <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
                    {uploadErrorMsg}
                  </p>
                )}

                {uploadResult ? (
                  <UploadResultPanel result={uploadResult} onReset={() => setUploadResult(null)} />
                ) : (
                  <button
                    type="button"
                    disabled={isUploading || !file}
                    onClick={() => uploadFile()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md text-sm transition-colors"
                  >
                    {isUploading && <Spinner size="sm" />}
                    {isUploading ? "Importing…" : "Import File"}
                  </button>
                )}
              </div>
            )}
          </div>
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
        className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 underline"
      >
        Sync again
      </button>
    </div>
  );
}

function UploadResultPanel({
  result,
  onReset,
}: {
  result: ImportResult;
  onReset: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-4">
        <StatBox label="Parsed" value={result.trades_parsed} color="text-slate-400" />
        <StatBox label="Created" value={result.trades_created} color="text-emerald-400" />
        <StatBox label="Skipped" value={result.trades_skipped} color="text-amber-400" />
      </div>
      {result.warnings.length > 0 && (
        <ul className="space-y-1 max-h-32 overflow-y-auto">
          {result.warnings.map((w, i) => (
            <li key={i} className="text-xs text-amber-400 bg-amber-900/10 px-3 py-1.5 rounded">
              {w}
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={onReset}
        className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 underline"
      >
        Import another file
      </button>
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}
