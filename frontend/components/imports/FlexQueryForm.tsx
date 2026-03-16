/**
 * FlexQueryForm — form for IBKR Flex Query import.
 */

"use client";

import { useState } from "react";
import { useFlexImport } from "@/hooks/useFlexImport";
import { useAccounts } from "@/hooks/useAccounts";
import { Spinner } from "@/components/ui/Spinner";
import type { AxiosError } from "axios";

const INPUT_CLASS =
  "w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
const LABEL_CLASS = "block text-sm font-medium text-slate-300 mb-1";

export function FlexQueryForm() {
  const [queryId, setQueryId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [fromDate, setFromDate] = useState("");

  const { data: accounts, isLoading: loadingAccounts } = useAccounts();
  const { mutate: runFlex, isPending, error, data: result, reset } = useFlexImport();

  const errorMessage = (() => {
    if (!error) return null;
    const axiosErr = error as AxiosError<{ detail?: string }>;
    return (
      axiosErr.response?.data?.detail ??
      "Import failed. Check the Query ID and try again."
    );
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    reset();
    runFlex({
      query_id: queryId.trim(),
      account_id: accountId || null,
      from_date: fromDate || null,
    });
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        className="bg-slate-800 rounded-xl p-6 border border-slate-700 space-y-5"
      >
        {/* Query ID */}
        <div>
          <label htmlFor="flex-query-id" className={LABEL_CLASS}>
            Query ID{" "}
            <span className="text-red-400">*</span>
          </label>
          <input
            id="flex-query-id"
            type="text"
            required
            value={queryId}
            onChange={(e) => setQueryId(e.target.value)}
            placeholder="e.g. 123456"
            className={INPUT_CLASS}
          />
          <p className="text-xs text-slate-500 mt-1">
            Your IBKR Flex Query ID from the Client Portal.
          </p>
        </div>

        {/* Account */}
        <div>
          <label htmlFor="flex-account" className={LABEL_CLASS}>
            Account{" "}
            <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          {loadingAccounts ? (
            <div className="flex items-center gap-2 text-slate-500 text-sm">
              <Spinner size="sm" /> Loading accounts…
            </div>
          ) : (
            <select
              id="flex-account"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className={INPUT_CLASS}
            >
              <option value="">— No account —</option>
              {(accounts ?? []).map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.broker ?? "unknown"})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* From Date */}
        <div>
          <label htmlFor="flex-from-date" className={LABEL_CLASS}>
            From Date{" "}
            <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <input
            id="flex-from-date"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            className={INPUT_CLASS}
          />
        </div>

        {errorMessage && (
          <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
            {errorMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={isPending || !queryId.trim()}
          className="flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
        >
          {isPending && <Spinner size="sm" />}
          {isPending ? "Fetching…" : "Run Flex Import"}
        </button>
      </form>

      {/* Import result */}
      {result && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h3 className="text-base font-semibold text-slate-100 mb-4">
            Import Complete
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-slate-100">
                {result.trades_parsed}
              </p>
              <p className="text-xs text-slate-500 mt-1">Parsed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {result.trades_created}
              </p>
              <p className="text-xs text-slate-500 mt-1">Created</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-400">
                {result.trades_skipped}
              </p>
              <p className="text-xs text-slate-500 mt-1">Skipped</p>
            </div>
          </div>

          {result.warnings.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-amber-400 mb-2">
                Warnings ({result.warnings.length}):
              </p>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {result.warnings.map((w, i) => (
                  <li
                    key={i}
                    className="text-xs text-slate-400 bg-slate-900/50 px-3 py-1.5 rounded"
                  >
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
