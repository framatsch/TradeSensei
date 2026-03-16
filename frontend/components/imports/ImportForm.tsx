/**
 * ImportForm — tabbed import: File Upload and Flex Query.
 */

"use client";

import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import { useAccounts } from "@/hooks/useAccounts";
import { FlexQueryForm } from "./FlexQueryForm";
import { Spinner } from "@/components/ui/Spinner";
import type { ImportResult, ResponseEnvelope } from "@/lib/types";
import type { AxiosError } from "axios";

const BROKERS = [
  { value: "ibkr", label: "Interactive Brokers (IBKR)" },
  { value: "schwab", label: "Charles Schwab" },
];

type Tab = "upload" | "flex";

export function ImportForm() {
  const [activeTab, setActiveTab] = useState<Tab>("upload");
  const [broker, setBroker] = useState<string>("ibkr");
  const [accountId, setAccountId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: accounts, isLoading: loadingAccounts } = useAccounts();

  const { mutate: uploadFile, isPending, error } = useMutation<
    ImportResult,
    Error,
    void
  >({
    mutationFn: async () => {
      if (!file) throw new Error("No file selected.");
      const formData = new FormData();
      formData.append("broker", broker);
      if (accountId) formData.append("account_id", accountId);
      formData.append("file", file);
      const res = await apiClient.post<ResponseEnvelope<ImportResult>>(
        "/api/v1/imports/upload",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return res.data.data;
    },
    onSuccess: (data) => {
      setResult(data);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
  });

  const errorMessage = (() => {
    if (!error) return null;
    const axiosErr = error as AxiosError<{ detail?: string }>;
    return (
      axiosErr.response?.data?.detail ??
      "Import failed. Please check the file format."
    );
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    uploadFile();
  };

  return (
    <div className="space-y-6">
      {/* Tab switcher */}
      <div className="flex gap-4 border-b border-slate-700">
        {(["upload", "flex"] as Tab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "border-b-2 border-blue-500 text-blue-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "upload" ? "File Upload" : "Flex Query"}
          </button>
        ))}
      </div>

      {/* File Upload tab */}
      {activeTab === "upload" && (
        <div className="space-y-6">
          <form
            onSubmit={handleSubmit}
            className="bg-slate-800 rounded-xl p-6 border border-slate-700 space-y-5"
          >
            {/* Broker select */}
            <div>
              <label
                htmlFor="broker"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Broker
              </label>
              <select
                id="broker"
                value={broker}
                onChange={(e) => setBroker(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {BROKERS.map((b) => (
                  <option key={b.value} value={b.value}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Account select */}
            <div>
              <label
                htmlFor="account"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Account{" "}
                <span className="text-slate-500 font-normal">(optional)</span>
              </label>
              {loadingAccounts ? (
                <div className="flex items-center gap-2 text-slate-500 text-sm">
                  <Spinner size="sm" /> Loading accounts…
                </div>
              ) : (
                <select
                  id="account"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
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

            {/* File picker */}
            <div>
              <label
                htmlFor="file"
                className="block text-sm font-medium text-slate-300 mb-1"
              >
                Trade History File
              </label>
              <input
                ref={fileInputRef}
                id="file"
                type="file"
                accept=".csv,.xlsx,.xls"
                required
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full text-slate-300 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-blue-600 file:text-white file:cursor-pointer hover:file:bg-blue-700"
              />
              <p className="text-xs text-slate-500 mt-1">
                Supported formats: CSV, XLSX for IBKR Activity Statement or Schwab
                Trade History.
              </p>
            </div>

            {errorMessage && (
              <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
                {errorMessage}
              </p>
            )}

            <button
              type="submit"
              disabled={isPending || !file}
              className="flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium rounded-md transition-colors"
            >
              {isPending && <Spinner size="sm" />}
              {isPending ? "Importing…" : "Import Trades"}
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
      )}

      {/* Flex Query tab */}
      {activeTab === "flex" && <FlexQueryForm />}
    </div>
  );
}
