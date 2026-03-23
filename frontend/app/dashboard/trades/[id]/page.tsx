"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTrade, useUpdateTrade } from "@/hooks/useTrade";
import { NoteList } from "@/components/notes/NoteList";
import { TagBadge } from "@/components/tags/TagBadge";
import { Spinner } from "@/components/ui/Spinner";
import { TradeEditForm } from "@/components/trades/TradeEditForm";
import { MediaChartsCard } from "@/components/trades/MediaChartsCard";
import type { TradeUpdate } from "@/lib/types";
import type { AxiosError } from "axios";

function formatPrice(value: string | null): string {
  if (value === null) return "—";
  return `$${parseFloat(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

function formatDate(value: string | null): string {
  if (value === null) return "—";
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function PnlDisplay({ value, size = "normal" }: { value: string | null, size?: "normal" | "large" }) {
  if (value === null) return <span className="text-slate-500">—</span>;
  const num = parseFloat(value);
  const color = num >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400";
  const prefix = num >= 0 ? "+" : "";
  const sizeClasses = size === "large" ? "text-xl font-bold" : "font-semibold";
  return (
    <span className={`${sizeClasses} ${color}`}>
      {prefix}${Math.abs(num).toFixed(2)}
    </span>
  );
}

export default function TradeDetailPage() {
  const params = useParams();
  const tradeId = typeof params.id === "string" ? params.id : "";
  const { data: trade, isLoading, isError, error } = useTrade(tradeId);
  const { mutate: updateTrade, isPending: isSaving } = useUpdateTrade(tradeId);

  const [isEditing, setIsEditing] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !trade) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-red-400 font-medium mb-2">
          {isError ? "Failed to load trade." : "Trade not found."}
        </p>
        {isError && (
          <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        )}
        <Link
          href="/dashboard/trades"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
        >
          Back to Trades
        </Link>
      </div>
    );
  }

  const isLong = trade.direction === "LONG";
  const isOpen = !trade.closed_at;

  function handleSave(payload: TradeUpdate) {
    setSaveError(null);
    updateTrade(
      { ...payload, is_manually_edited: true },
      {
        onSuccess: () => {
          setIsEditing(false);
        },
        onError: (err) => {
          const axiosErr = err as AxiosError<{ detail?: string }>;
          setSaveError(
            axiosErr.response?.data?.detail ?? "Failed to save trade."
          );
        },
      }
    );
  }

  // ── Performance calculations (all from trade data, no mocks) ──
  const qty = parseFloat(trade.quantity);
  const entryP = parseFloat(trade.entry_price);
  const exitP = trade.exit_price ? parseFloat(trade.exit_price) : null;
  const stopP = trade.stop_loss ? parseFloat(trade.stop_loss) : null;
  const takePP = trade.take_profit ? parseFloat(trade.take_profit) : null;
  const pnlVal = trade.pnl ? parseFloat(trade.pnl) : null;
  const commVal = parseFloat(trade.commission ?? "0");

  // Initial risk in $ (per-share risk × position size)
  const riskPerShare = stopP !== null ? Math.abs(entryP - stopP) : null;
  const initialRisk = riskPerShare !== null ? riskPerShare * qty : null;

  // Realized R-multiple (pnl / initial risk)
  const realizedR = pnlVal !== null && initialRisk !== null && initialRisk > 0
    ? pnlVal / initialRisk
    : null;

  // Planned RRR from TP/SL
  const plannedRrr = stopP !== null && takePP !== null && riskPerShare! > 0
    ? Math.abs(takePP - entryP) / riskPerShare!
    : null;

  // Return % on capital deployed
  const capitalDeployed = entryP * qty;
  const returnPct = pnlVal !== null && capitalDeployed > 0
    ? (pnlVal / capitalDeployed) * 100
    : null;

  // Net P&L after commissions (already in pnl? show gross vs net)
  const grossPnl = exitP !== null
    ? (isLong ? (exitP - entryP) : (entryP - exitP)) * qty
    : null;
  const netPnl = grossPnl !== null ? grossPnl - commVal : null;

  // Holding period
  function formatHoldingPeriod(from: string, to: string | null): string {
    if (!to) return "Ongoing";
    const ms = new Date(to).getTime() - new Date(from).getTime();
    const totalMins = Math.floor(ms / 60000);
    const days = Math.floor(totalMins / 1440);
    const hours = Math.floor((totalMins % 1440) / 60);
    const mins = totalMins % 60;
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Back link */}
      <div>
        <Link
          href="/dashboard/trades"
          className="inline-flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100 transition-colors"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-4 h-4"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back to Trades
        </Link>
      </div>

      {/* Edit form override */}
      {isEditing ? (
        <TradeEditForm
          trade={trade}
          onSave={handleSave}
          onCancel={() => {
            setIsEditing(false);
            setSaveError(null);
          }}
          isSaving={isSaving}
          saveError={saveError}
        />
      ) : (
        <>
          {/* Dashboard Header Area */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-800 p-5 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{trade.symbol}</h1>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium ${
                    isLong
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                      : "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400 border border-red-200 dark:border-red-800"
                  }`}
                >
                  {trade.direction}
                </span>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-600">
                  {trade.asset_class}
                </span>
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                Opened: {formatDate(trade.opened_at)} {trade.closed_at && `• Closed: ${formatDate(trade.closed_at)}`}
              </div>
            </div>

              <div className="flex items-center gap-6">
               <div className="flex flex-col items-end">
                 <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Final P&L</span>
                 <PnlDisplay value={trade.pnl} size="large" />
               </div>
               <div className="flex flex-col items-end gap-2">
                 <div className="flex items-center gap-1.5">
                   {trade.is_manually_edited && (
                     <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
                       Manually Edited
                     </span>
                   )}
                   <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide ${
                     isOpen 
                       ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                       : "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-600"
                   }`}>
                     {isOpen ? "Open" : "Closed"}
                   </span>
                 </div>
                 <button
                   onClick={() => setIsEditing(true)}
                   className="text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                 >
                   Edit Trade
                 </button>
               </div>
             </div>
          </div>

          {/* Grid Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left Column (60-70%) */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Media & Charts */}
              <MediaChartsCard trade={trade} />

              {/* Execution Details */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">Execution Details</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-y-6 gap-x-4">
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Entry Price</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{formatPrice(trade.entry_price)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Exit Price</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{formatPrice(trade.exit_price)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Quantity</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{trade.quantity}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Fees / Commissions</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{formatPrice(trade.commission)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Stop Loss</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{formatPrice(trade.stop_loss)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 mb-1">Take Profit</dt>
                    <dd className="font-medium text-slate-900 dark:text-slate-100">{formatPrice(trade.take_profit)}</dd>
                  </div>
                </div>
              </div>

              {/* Journal & Notes */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4 flex justify-between items-center">
                  Journal & Notes
                  {trade.trade_notes.length > 0 && (
                    <span className="text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full text-slate-600 dark:text-slate-300">
                      {trade.trade_notes.length}
                    </span>
                  )}
                </h2>
                {trade.notes && (
                  <div className="mb-4 pb-4 border-b border-slate-100 dark:border-slate-700/50">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">General Note</div>
                    <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{trade.notes}</p>
                  </div>
                )}
                <NoteList tradeId={trade.id} />
              </div>

            </div>

            {/* Right Column (30-40%) */}
            <div className="space-y-6">
              
              {/* Performance Metrics */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">Performance</h2>
                <div className="space-y-3">

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Realized R</span>
                    <span className={`font-semibold ${realizedR === null ? "text-slate-400" : realizedR >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
                      {realizedR !== null ? `${realizedR >= 0 ? "+" : ""}${realizedR.toFixed(2)}R` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Planned RRR</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {plannedRrr !== null ? `1 : ${plannedRrr.toFixed(2)}` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Initial Risk</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {initialRisk !== null ? `$${initialRisk.toFixed(2)}` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Return %</span>
                    <span className={`font-medium ${returnPct === null ? "text-slate-400" : returnPct >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
                      {returnPct !== null ? `${returnPct >= 0 ? "+" : ""}${returnPct.toFixed(2)}%` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Gross P&L</span>
                    <span className={`font-medium ${grossPnl === null ? "text-slate-400" : grossPnl >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
                      {grossPnl !== null ? `${grossPnl >= 0 ? "+" : ""}$${Math.abs(grossPnl).toFixed(2)}` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-700/50">
                    <span className="text-sm text-slate-500">Net P&L (after fees)</span>
                    <span className={`font-medium ${netPnl === null ? "text-slate-400" : netPnl >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
                      {netPnl !== null ? `${netPnl >= 0 ? "+" : ""}$${Math.abs(netPnl).toFixed(2)}` : "—"}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-500">Holding Period</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {formatHoldingPeriod(trade.opened_at, trade.closed_at)}
                    </span>
                  </div>

                </div>
              </div>

              {/* Playbook & Psychology */}
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
                <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">Playbook & Psychology</h2>
                <div className="space-y-4">
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Strategy / Setup</div>
                    {trade.playbook_name ? (
                      <span className="text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded">
                        {trade.playbook_name}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-400 italic">No playbook assigned</span>
                    )}
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 mb-2">Tags</div>
                    {trade.tags.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {trade.tags.map((tag) => (
                          <TagBadge key={tag.id} tag={tag} />
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400 italic">No tags</span>
                    )}
                  </div>
                </div>
              </div>

            </div>
          </div>
        </>
      )}
    </div>
  );
}
