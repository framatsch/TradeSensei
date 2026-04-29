/**
 * MergePreviewModal — shows source trade cards and merged result preview
 * before confirming a multi-trade merge.
 */

"use client";

import { ArrowRight, AlertTriangle, Loader2 } from "lucide-react";
import type { Trade } from "@/lib/types";
import { useMergeTrades } from "@/hooks/useMergeTrades";
import { useState } from "react";
import { extractApiError } from "@/lib/api/errors";

interface Props {
  trades: Trade[];
  onClose: () => void;
  /** Called with the surviving (merged) trade ID on success. */
  onSuccess?: (survivorId: string) => void;
}

function fmt(v: string | null, prefix = "$"): string {
  if (v === null) return "—";
  const n = parseFloat(v);
  return `${prefix}${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function pnlColor(v: string | null): string {
  if (v === null) return "text-muted-foreground";
  return parseFloat(v) >= 0
    ? "text-emerald-500 dark:text-emerald-400"
    : "text-red-500 dark:text-red-400";
}

function TradeCard({ trade }: { trade: Trade }) {
  return (
    <div className="flex-1 min-w-0 rounded-lg border border-border bg-secondary p-3 space-y-1.5 text-sm">
      <div className="flex items-center gap-1.5">
        <span className="font-semibold text-foreground truncate">{trade.symbol}</span>
        <span
          className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
            trade.direction === "LONG"
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
              : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
          }`}
        >
          {trade.direction}
        </span>
      </div>
      <div className="text-xs text-muted-foreground">
        Qty: <span className="text-foreground">{trade.quantity === null ? "—" : parseFloat(trade.quantity).toLocaleString()}</span>
      </div>
      <div className="text-xs text-muted-foreground">
        Executions: <span className="text-foreground">{trade.trade_notes?.length ?? "—"}</span>
      </div>
      <div className={`text-xs font-medium ${pnlColor(trade.pnl)}`}>
        {trade.pnl !== null
          ? `${parseFloat(trade.pnl) >= 0 ? "+" : ""}${fmt(trade.pnl)}`
          : "Open"}
      </div>
    </div>
  );
}

export function MergePreviewModal({ trades, onClose, onSuccess }: Props) {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const mergeTrades = useMergeTrades();

  // Compute combined values for preview
  const totalQty = trades.reduce((sum, t) => sum + (t.quantity === null ? 0 : parseFloat(t.quantity)), 0);
  const totalPnl = trades.reduce((sum, t) => sum + (t.pnl ? parseFloat(t.pnl) : 0), 0);
  const hasPnl = trades.some((t) => t.pnl !== null);
  const symbol = trades[0]?.symbol ?? "—";

  const handleMerge = () => {
    setErrorMsg(null);
    const ids = trades.map((t) => t.id);
    mergeTrades.mutate(
      { trade_ids: ids },
      {
        onSuccess: (survivor) => {
          onSuccess?.(survivor.id);
          onClose();
        },
        onError: (err) => {
          setErrorMsg(extractApiError(err, "Failed to merge trades."));
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-card border border-border shadow-xl p-6">
        <h2 className="text-lg font-bold text-foreground mb-1">Merge Trades</h2>
        <p className="text-sm text-muted-foreground mb-5">
          All execution legs will be moved to the oldest trade. This action cannot be undone.
        </p>

        {/* Warning */}
        <div className="flex items-start gap-2 mb-5 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-3 py-2.5">
          <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <span className="text-xs text-amber-700 dark:text-amber-400">
            Merging is irreversible. The non-surviving trades will be permanently deleted.
          </span>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-900/20 border border-red-800 p-3 text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        {/* Source trade cards + arrow */}
        <div className="flex items-center gap-2 mb-5 overflow-x-auto">
          {trades.map((t, i) => (
            <div key={t.id} className="flex items-center gap-2 flex-shrink-0">
              <TradeCard trade={t} />
              {i < trades.length - 1 && (
                <ArrowRight size={16} className="text-muted-foreground flex-shrink-0" />
              )}
            </div>
          ))}
        </div>

        {/* Result preview */}
        <div className="rounded-lg border border-[#6063dd]/30 bg-[#6063dd]/5 p-3 mb-6 text-sm space-y-1.5">
          <div className="text-xs font-semibold text-[#6063dd] uppercase tracking-wide mb-2">
            Merged Result
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Symbol</span>
            <span className="font-medium text-foreground">{symbol}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Combined Qty</span>
            <span className="font-medium text-foreground">{totalQty.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Combined P&L</span>
            <span className={`font-medium ${hasPnl ? pnlColor(totalPnl >= 0 ? "1" : "-1") : "text-muted-foreground"}`}>
              {hasPnl
                ? `${totalPnl >= 0 ? "+" : ""}$${Math.abs(totalPnl).toFixed(2)}`
                : "—"}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Execution legs</span>
            <span className="font-medium text-foreground">{trades.length} trades → 1</span>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleMerge}
            disabled={mergeTrades.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
          >
            {mergeTrades.isPending && <Loader2 size={14} className="animate-spin" />}
            Merge Trades
          </button>
        </div>
      </div>
    </div>
  );
}
