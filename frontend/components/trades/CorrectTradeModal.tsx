/**
 * CorrectTradeModal — small modal for rare trade identity corrections.
 * Allows editing Symbol and Asset Class only. Sets is_manually_edited=true on save.
 */

"use client";

import { useState } from "react";
import type { AssetClass, Trade } from "@/lib/types";
import { useUpdateTrade } from "@/hooks/useTrade";

interface Props {
  trade: Trade;
  onClose: () => void;
}

const ASSET_CLASSES: AssetClass[] = ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"];

export function CorrectTradeModal({ trade, onClose }: Props) {
  const [symbol, setSymbol] = useState(trade.symbol);
  const [assetClass, setAssetClass] = useState<AssetClass>(trade.asset_class ?? "EQUITY");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const updateTrade = useUpdateTrade(trade.id);

  const inputCls =
    "w-full rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";
  const labelCls = "mb-1 block text-sm font-medium text-muted-foreground";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed) {
      setErrorMsg("Symbol is required.");
      return;
    }

    updateTrade.mutate(
      {
        symbol: trimmed,
        asset_class: assetClass,
        is_manually_edited: true,
      },
      {
        onSuccess: () => onClose(),
        onError: (err) => {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          setErrorMsg(axiosErr.response?.data?.detail ?? "Failed to save correction.");
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-sm rounded-xl bg-card p-6 shadow-xl border border-border">
        <h2 className="mb-1 text-lg font-bold text-foreground">Correct Trade</h2>
        <p className="mb-5 text-xs text-muted-foreground">
          These fields affect trade identity. Only change them to fix import errors.
        </p>

        {/* Warning banner */}
        <div className="mb-5 flex items-start gap-2 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-3 py-2.5">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span className="text-xs text-amber-700 dark:text-amber-400">
            Saving will mark this trade as manually edited and may affect aggregation.
          </span>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-900/20 border border-red-800 p-3 text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Symbol */}
          <div>
            <label className={labelCls}>Symbol</label>
            <input
              type="text"
              className={inputCls}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL"
              required
            />
          </div>

          {/* Asset Class */}
          <div>
            <label className={labelCls}>Asset Class</label>
            <select
              className={inputCls}
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value as AssetClass)}
            >
              {ASSET_CLASSES.map((ac) => (
                <option key={ac} value={ac}>
                  {ac}
                </option>
              ))}
            </select>
          </div>

          {/* Read-only info */}
          <div className="rounded-md bg-secondary px-3 py-2.5 space-y-1.5 text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Direction</span>
              <span className="font-medium text-foreground">{trade.direction}</span>
            </div>
            <div className="flex justify-between">
              <span>Currency</span>
              <span className="font-medium text-foreground">{trade.currency ?? "—"}</span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateTrade.isPending}
              className="rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              {updateTrade.isPending ? "Saving…" : "Save Correction"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
