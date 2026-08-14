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

"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Check, X, MoreHorizontal, Split } from "lucide-react";
import { useTrade, useUpdateTrade } from "@/hooks/useTrade";
import { useTradeExecutions } from "@/hooks/useExecutions";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { NoteList } from "@/components/notes/NoteList";
import { Spinner } from "@/components/ui/Spinner";
import { MediaChartsCard } from "@/components/trades/MediaChartsCard";
import { ExecutionSummaryCard } from "@/components/trades/ExecutionSummaryCard";
import { ExecutionLegsTable } from "@/components/trades/ExecutionLegsTable";
import { MetricHelpLink } from "@/components/ui/MetricHelpLink";
import { CorrectTradeModal } from "@/components/trades/CorrectTradeModal";
import { TradePickerModal } from "@/components/trades/TradePickerModal";
import { MergePreviewModal } from "@/components/trades/MergePreviewModal";
import { QualitativeMetadataPanel } from "@/components/trades/QualitativeMetadataPanel";
import { ConflictBanner } from "@/components/trades/ConflictBanner";
import { formatSplitRatio } from "@/lib/formatSplitRatio";

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

function PnlDisplay({
  value,
  size = "normal",
}: {
  value: string | null;
  size?: "normal" | "large";
}) {
  if (value === null) return <span className="text-muted-foreground">—</span>;
  const num = parseFloat(value);
  const color =
    num >= 0
      ? "text-emerald-500 dark:text-emerald-400"
      : "text-red-500 dark:text-red-400";
  const prefix = num >= 0 ? "+" : "";
  const sizeClasses = size === "large" ? "text-xl font-bold" : "font-semibold";
  return (
    <span className={`${sizeClasses} ${color}`}>
      {prefix}${Math.abs(num).toFixed(2)}
    </span>
  );
}

// ── Inline number editor for SL / TP ─────────────────────────────────────────

interface InlineNumberFieldProps {
  label: string;
  value: string | null;
  onSave: (value: string | null) => void;
  helpAnchor?: string;
}

function InlineNumberField({ label, value, onSave, helpAnchor }: InlineNumberFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value ?? "");
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [editing, value]);

  const handleSave = () => {
    const trimmed = draft.trim();
    onSave(trimmed === "" ? null : trimmed);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex justify-between items-center">
        <span className="text-sm text-muted-foreground flex items-center gap-1.5">
          {label}
          {helpAnchor && <MetricHelpLink anchor={helpAnchor} />}
        </span>
        <div className="flex items-center gap-1">
          <input
            ref={inputRef}
            type="number"
            step="any"
            className="w-24 rounded border border-border bg-secondary px-2 py-0.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary text-right"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="0.00"
          />
          <button
            type="button"
            onClick={handleSave}
            className="p-0.5 rounded text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/30"
          >
            <Check size={14} />
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="p-0.5 rounded text-muted-foreground hover:bg-secondary"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-muted-foreground flex items-center gap-1.5">
        {label}
        {helpAnchor && <MetricHelpLink anchor={helpAnchor} />}
      </span>
      <button
        type="button"
        onClick={() => setEditing(true)}
        className="font-medium text-foreground hover:text-primary hover:underline underline-offset-2 transition-colors text-sm"
        title={`Click to edit ${label}`}
      >
        {value !== null ? `$${parseFloat(value).toFixed(2)}` : <span className="text-zinc-400 italic">—</span>}
      </button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TradeDetailPage() {
  const params = useParams();
  const tradeId = typeof params.id === "string" ? params.id : "";
  const { activePortfolioId } = useActivePortfolio();
  const { data: trade, isLoading, isError, error } = useTrade(tradeId);
  const { data: executions = [] } = useTradeExecutions(tradeId, activePortfolioId);
  const updateTrade = useUpdateTrade(tradeId);
  const quickNotesEnabled = useFeatureFlag("enable_quick_notes");
  const [correctModalOpen, setCorrectModalOpen] = useState(false);
  const [overflowOpen, setOverflowOpen] = useState(false);
  const [tradePickerOpen, setTradePickerOpen] = useState(false);
  const [mergeTargets, setMergeTargets] = useState<import("@/lib/types").Trade[]>([]);
  const [mergePreviewOpen, setMergePreviewOpen] = useState(false);
  const overflowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!overflowOpen) return;
    function handleClick(e: MouseEvent) {
      if (!overflowRef.current?.contains(e.target as Node)) {
        setOverflowOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [overflowOpen]);

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
          <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        )}
        <Link
          href="/dashboard/trades"
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm transition-colors"
        >
          Back to Trades
        </Link>
      </div>
    );
  }

  const isLong = trade.direction === "LONG";
  const isCombo = trade.is_combo;
  const isOpen = !trade.closed_at;
  const headerQuantity = trade.chart_quantity ?? trade.quantity;
  const headerEntryPrice = trade.chart_entry_price ?? trade.entry_price;
  const headerExitPrice = trade.chart_exit_price ?? trade.exit_price;

  // ── Performance calculations ──────────────────────────────────────────────
  const qty = headerQuantity === null ? 0 : parseFloat(headerQuantity);
  const riskEntryP = trade.entry_price === null ? 0 : parseFloat(trade.entry_price);
  const basisEntryP = headerEntryPrice === null ? 0 : parseFloat(headerEntryPrice);
  const exitP = headerExitPrice ? parseFloat(headerExitPrice) : null;
  const stopP = trade.stop_loss ? parseFloat(trade.stop_loss) : null;
  const takePP = trade.take_profit ? parseFloat(trade.take_profit) : null;
  const pnlVal = trade.pnl ? parseFloat(trade.pnl) : null;
  const commVal = parseFloat(trade.commission ?? "0");

  const riskPerShare = stopP !== null ? Math.abs(riskEntryP - stopP) : null;
  const initialRisk = riskPerShare !== null ? riskPerShare * qty : null;
  const realizedR =
    pnlVal !== null && initialRisk !== null && initialRisk > 0
      ? pnlVal / initialRisk
      : null;
  const plannedRrr =
    stopP !== null && takePP !== null && riskPerShare! > 0
      ? Math.abs(takePP - riskEntryP) / riskPerShare!
      : null;
  const capitalDeployed = basisEntryP * qty;
  const returnPct =
    pnlVal !== null && capitalDeployed > 0
      ? (pnlVal / capitalDeployed) * 100
      : null;
  const grossPnl =
    exitP !== null
      ? (isLong ? exitP - basisEntryP : basisEntryP - exitP) * qty
      : null;
  const netPnl = grossPnl !== null ? grossPnl - commVal : null;

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

  // ── Save handlers ─────────────────────────────────────────────────────────

  const handleSaveStopLoss = (value: string | null) => {
    updateTrade.mutate({ stop_loss: value });
  };

  const handleSaveTakeProfit = (value: string | null) => {
    updateTrade.mutate({ take_profit: value });
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div>
        <Link
          href="/dashboard/trades"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
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

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 solid-card p-5 shadow-sm">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{trade.symbol}</h1>
              {trade.corporate_action_impact && trade.corporate_action_impact.length > 0 && (
                <span
                  className="inline-flex text-muted-foreground hover:text-foreground cursor-help"
                  tabIndex={0}
                  title={
                    "Affected by a corporate action. Values may differ across the table, " +
                    "the chart, and the as-traded price — see the execution legs below for the " +
                    "reconciled per-leg values.\n" +
                    trade.corporate_action_impact
                      .map((a) => {
                        const remap =
                          a.old_conid && a.new_conid && a.old_conid !== a.new_conid
                            ? " (Symbol changed)"
                            : "";
                        return `Split ${formatSplitRatio(a.ratio)} on ${a.date}${remap}`;
                      })
                      .join("\n")
                  }
                  aria-label="Affected by a corporate action"
                >
                  <Split className="w-5 h-5" />
                </span>
              )}
            </div>
            {trade.direction && !isCombo && (
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium ${
                  isLong
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                    : "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400 border border-red-200 dark:border-red-800"
                }`}
              >
                {trade.direction}
              </span>
            )}
            <span className="inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium bg-secondary text-muted-foreground border border-border">
              {isCombo ? "COMBO" : trade.asset_class}
            </span>
          </div>
          <div className="text-sm text-muted-foreground">
            Opened: {formatDate(trade.opened_at)}{" "}
            {trade.closed_at && `• Closed: ${formatDate(trade.closed_at)}`}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Final P&L
            </span>
            <PnlDisplay value={trade.pnl} size="large" />
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-1.5">
              {trade.is_manually_edited && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400 border border-violet-200 dark:border-violet-800">
                  Manually Edited
                </span>
              )}
              <span
                className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wide ${
                  isOpen
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                    : "bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300 border border-border"
                }`}
              >
                {isOpen ? "Open" : "Closed"}
              </span>
            </div>
          </div>
          {/* Actions */}
          <div className="flex items-center gap-1.5 border-l border-border pl-4">
            {/* Overflow menu */}
            <div ref={overflowRef} className="relative">
            <button
              type="button"
              onClick={() => setOverflowOpen((o) => !o)}
              className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              aria-label="Trade actions"
            >
              <MoreHorizontal size={18} />
            </button>
            {overflowOpen && (
              <div className="absolute right-0 top-full mt-1 z-30 w-44 rounded-lg border border-border bg-card shadow-lg py-1 text-sm">
                <button
                  type="button"
                  className="w-full px-4 py-2 text-left text-foreground hover:bg-secondary transition-colors"
                  onClick={() => { setCorrectModalOpen(true); setOverflowOpen(false); }}
                >
                  Correct Trade…
                </button>
                <button
                  type="button"
                  className="w-full px-4 py-2 text-left text-foreground hover:bg-secondary transition-colors"
                  onClick={() => { setTradePickerOpen(true); setOverflowOpen(false); }}
                >
                  Merge with…
                </button>
              </div>
            )}
          </div>
          </div>
        </div>
      </div>

      {/* Conflict Banner */}
      {trade.has_conflict && (
        <ConflictBanner
          onReview={() => {
            document.getElementById("executions-table")?.scrollIntoView({ behavior: "smooth" });
          }}
        />
      )}


      {/* Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Media & Charts */}
        <div className="lg:col-span-2">
          <MediaChartsCard trade={trade} executions={executions} className="h-full min-h-[400px] lg:min-h-[520px]" />
        </div>

        {/* Right Column: Performance Metrics */}
        <div className="lg:col-span-1">
          <div className="solid-card p-5 shadow-sm h-full flex flex-col">
            <h2 className="text-base font-semibold text-foreground mb-4">
              Performance
            </h2>
            <div className="space-y-3 flex-1">
              <InlineNumberField
                label="Stop Loss"
                value={trade.stop_loss}
                onSave={handleSaveStopLoss}
                helpAnchor="stop-loss"
              />
              <InlineNumberField
                label="Take Profit"
                value={trade.take_profit}
                onSave={handleSaveTakeProfit}
                helpAnchor="take-profit"
              />

              {/* Divider */}
              <div className="border-t border-border pt-3 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Realized R <MetricHelpLink anchor="realized-r" />
                  </span>
                  <span
                    className={`font-semibold ${
                      realizedR === null
                        ? "text-zinc-400"
                        : realizedR >= 0
                        ? "text-emerald-500 dark:text-emerald-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {realizedR !== null
                      ? `${realizedR >= 0 ? "+" : ""}${realizedR.toFixed(2)}R`
                      : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Planned RRR <MetricHelpLink anchor="planned-rrr" />
                  </span>
                  <span className="font-medium text-foreground">
                    {plannedRrr !== null ? `1 : ${plannedRrr.toFixed(2)}` : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Initial Risk <MetricHelpLink anchor="initial-risk" />
                  </span>
                  <span className="font-medium text-foreground">
                    {initialRisk !== null ? `$${initialRisk.toFixed(2)}` : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Return % <MetricHelpLink anchor="return-pct" />
                  </span>
                  <span
                    className={`font-medium ${
                      returnPct === null
                        ? "text-zinc-400"
                        : returnPct >= 0
                        ? "text-emerald-500 dark:text-emerald-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {returnPct !== null
                      ? `${returnPct >= 0 ? "+" : ""}${returnPct.toFixed(2)}%`
                      : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Gross P&L <MetricHelpLink anchor="gross-pnl-trade" />
                  </span>
                  <span
                    className={`font-medium ${
                      grossPnl === null
                        ? "text-zinc-400"
                        : grossPnl >= 0
                        ? "text-emerald-500 dark:text-emerald-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {grossPnl !== null
                      ? `${grossPnl >= 0 ? "+" : ""}$${Math.abs(grossPnl).toFixed(2)}`
                      : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Net P&L <MetricHelpLink anchor="net-pnl-trade" />
                  </span>
                  <span
                    className={`font-medium ${
                      netPnl === null
                        ? "text-zinc-400"
                        : netPnl >= 0
                        ? "text-emerald-500 dark:text-emerald-400"
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {netPnl !== null
                      ? `${netPnl >= 0 ? "+" : ""}$${Math.abs(netPnl).toFixed(2)}`
                      : "—"}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Holding Period <MetricHelpLink anchor="holding-period" />
                  </span>
                  <span className="font-medium text-foreground">
                    {formatHoldingPeriod(trade.opened_at, trade.closed_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Summary (Full Width) */}
      <section className="w-full">
        <ExecutionSummaryCard trade={trade} executions={executions} />
      </section>

      {/* Qualitative Analysis & Metadata */}
      <section className="w-full">
        <QualitativeMetadataPanel trade={trade} portfolioId={activePortfolioId ?? ""} />
      </section>

      {/* Quick Notes */}
      {quickNotesEnabled && (
        <section className="w-full">
          <NoteList tradeId={trade.id} />
        </section>
      )}

      {/* Execution Legs Table */}
      <section className="w-full" id="executions-table">
        <ExecutionLegsTable tradeId={trade.id} trade={trade} />
      </section>

      {/* Correct Trade Modal */}
      {correctModalOpen && (
        <CorrectTradeModal
          trade={trade}
          onClose={() => setCorrectModalOpen(false)}
        />
      )}

      {/* Trade Picker for merge */}
      {tradePickerOpen && (
        <TradePickerModal
          filterSymbol={trade.symbol}
          excludeIds={[trade.id]}
          singleSelect
          confirmLabel="Continue"
          onConfirm={(picked) => {
            setMergeTargets([trade, ...picked]);
            setTradePickerOpen(false);
            setMergePreviewOpen(true);
          }}
          onClose={() => setTradePickerOpen(false)}
        />
      )}

      {/* Merge Preview */}
      {mergePreviewOpen && mergeTargets.length >= 2 && (
        <MergePreviewModal
          trades={mergeTargets}
          onClose={() => { setMergePreviewOpen(false); setMergeTargets([]); }}
        />
      )}
    </div>
  );
}
