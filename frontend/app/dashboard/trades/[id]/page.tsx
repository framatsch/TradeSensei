"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Check, X, ChevronDown, MoreHorizontal } from "lucide-react";
import { useTrade, useUpdateTrade } from "@/hooks/useTrade";
import { useTradeExecutions } from "@/hooks/useExecutions";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useTags } from "@/hooks/useTags";
import { NoteList } from "@/components/notes/NoteList";
import { TagBadge } from "@/components/tags/TagBadge";
import { Spinner } from "@/components/ui/Spinner";
import { MediaChartsCard } from "@/components/trades/MediaChartsCard";
import { ExecutionSummaryCard } from "@/components/trades/ExecutionSummaryCard";
import { ExecutionLegsTable } from "@/components/trades/ExecutionLegsTable";
import { MetricHelpLink } from "@/components/ui/MetricHelpLink";
import { CorrectTradeModal } from "@/components/trades/CorrectTradeModal";
import { TradePickerModal } from "@/components/trades/TradePickerModal";
import { MergePreviewModal } from "@/components/trades/MergePreviewModal";
import type { Tag } from "@/lib/types";

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

// ── Inline playbook dropdown ──────────────────────────────────────────────────

interface InlinePlaybookFieldProps {
  playbookId: string | null;
  playbookName: string | null;
  onSave: (playbookId: string | null) => void;
}

function InlinePlaybookField({ playbookId, playbookName, onSave }: InlinePlaybookFieldProps) {
  const [editing, setEditing] = useState(false);
  const { data: playbooks = [] } = usePlaybooks();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!editing) return;
    function handleClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        setEditing(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [editing]);

  const handleSelect = (id: string | null) => {
    onSave(id);
    setEditing(false);
  };

  if (editing) {
    return (
      <div ref={containerRef} className="relative">
        <div className="absolute right-0 top-0 z-20 w-52 rounded-lg border border-border bg-card shadow-lg py-1 text-sm max-h-56 overflow-y-auto">
          <button
            type="button"
            className={`w-full px-3 py-2 text-left hover:bg-secondary transition-colors ${
              playbookId === null ? "text-primary font-medium" : "text-muted-foreground"
            }`}
            onClick={() => handleSelect(null)}
          >
            None
          </button>
          {playbooks.map((pb) => (
            <button
              key={pb.id}
              type="button"
              className={`w-full px-3 py-2 text-left hover:bg-secondary transition-colors ${
                pb.id === playbookId ? "text-primary font-medium" : "text-foreground"
              }`}
              onClick={() => handleSelect(pb.id)}
            >
              {pb.name}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="inline-flex items-center gap-1 text-sm font-medium text-primary bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded hover:opacity-80 transition-opacity"
      title="Click to change playbook"
    >
      {playbookName ?? <span className="text-zinc-400 font-normal italic">No playbook assigned</span>}
      <ChevronDown size={12} className="opacity-60" />
    </button>
  );
}

// ── Inline tag picker ─────────────────────────────────────────────────────────

interface InlineTagsFieldProps {
  tagIds: string[];
  tags: Pick<Tag, "id" | "name" | "color">[];
  onSave: (tagIds: string[]) => void;
}

function InlineTagsField({ tagIds, tags: tradeTags, onSave }: InlineTagsFieldProps) {
  const [editing, setEditing] = useState(false);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<string[]>(tagIds);
  const { data: allTags = [] } = useTags();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (editing) setDraft(tagIds);
  }, [editing, tagIds]);

  useEffect(() => {
    if (!editing) return;
    function handleClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) {
        onSave(draft);
        setEditing(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [editing, draft, onSave]);

  const filtered = allTags.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (id: string) => {
    setDraft((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  if (editing) {
    return (
      <div ref={containerRef} className="relative">
        <div className="absolute right-0 top-0 z-20 w-60 rounded-lg border border-border bg-card shadow-lg py-2 text-sm">
          <div className="px-3 pb-2">
            <input
              autoFocus
              type="text"
              className="w-full rounded border border-border bg-secondary px-2 py-1 text-xs focus:border-primary focus:outline-none"
              placeholder="Search tags…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted-foreground">No tags found</div>
            )}
            {filtered.map((tag) => (
              <button
                key={tag.id}
                type="button"
                className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-secondary transition-colors"
                onClick={() => toggle(tag.id)}
              >
                <span
                  className={`flex h-4 w-4 items-center justify-center rounded border transition-colors ${
                    draft.includes(tag.id)
                      ? "bg-[#6063dd] border-[#6063dd]"
                      : "border-border"
                  }`}
                >
                  {draft.includes(tag.id) && <Check size={10} className="text-white" />}
                </span>
                <span
                  className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: tag.color ?? "#475569" }}
                />
                <span className="text-foreground truncate">{tag.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="w-full text-left group"
      title="Click to edit tags"
    >
      {tradeTags.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {tradeTags.map((tag) => (
            <TagBadge key={tag.id} tag={tag} />
          ))}
        </div>
      ) : (
        <span className="text-sm text-zinc-400 italic group-hover:text-foreground transition-colors">
          No tags — click to add
        </span>
      )}
    </button>
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

  // ── Performance calculations ──────────────────────────────────────────────
  const qty = trade.quantity === null ? 0 : parseFloat(trade.quantity);
  const entryP = trade.entry_price === null ? 0 : parseFloat(trade.entry_price);
  const exitP = trade.exit_price ? parseFloat(trade.exit_price) : null;
  const stopP = trade.stop_loss ? parseFloat(trade.stop_loss) : null;
  const takePP = trade.take_profit ? parseFloat(trade.take_profit) : null;
  const pnlVal = trade.pnl ? parseFloat(trade.pnl) : null;
  const commVal = parseFloat(trade.commission ?? "0");

  const riskPerShare = stopP !== null ? Math.abs(entryP - stopP) : null;
  const initialRisk = riskPerShare !== null ? riskPerShare * qty : null;
  const realizedR =
    pnlVal !== null && initialRisk !== null && initialRisk > 0
      ? pnlVal / initialRisk
      : null;
  const plannedRrr =
    stopP !== null && takePP !== null && riskPerShare! > 0
      ? Math.abs(takePP - entryP) / riskPerShare!
      : null;
  const capitalDeployed = entryP * qty;
  const returnPct =
    pnlVal !== null && capitalDeployed > 0
      ? (pnlVal / capitalDeployed) * 100
      : null;
  const grossPnl =
    exitP !== null
      ? (isLong ? exitP - entryP : entryP - exitP) * qty
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

  const handleSavePlaybook = (playbookId: string | null) => {
    updateTrade.mutate({ playbook_id: playbookId });
  };

  const handleSaveTags = (tagIds: string[]) => {
    updateTrade.mutate({ tag_ids: tagIds });
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card p-5 rounded-xl border border-border shadow-sm">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">{trade.symbol}</h1>
            {isCombo ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium bg-muted text-foreground border border-border">
                COMBO
              </span>
            ) : (
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

      {/* Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Media & Charts */}
          <MediaChartsCard trade={trade} executions={executions} />

          {/* Execution Summary */}
          <ExecutionSummaryCard trade={trade} executions={executions} />

          {/* Execution Legs Table */}
          <ExecutionLegsTable tradeId={trade.id} trade={trade} />

          {/* Journal & Notes */}
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
            <h2 className="text-base font-semibold text-foreground mb-4 flex justify-between items-center">
              Journal &amp; Notes
              {trade.trade_notes.length > 0 && (
                <span className="text-xs bg-secondary px-2 py-0.5 rounded-full text-zinc-600 dark:text-zinc-300">
                  {trade.trade_notes.length}
                </span>
              )}
            </h2>
            {trade.notes && (
              <div className="mb-4 pb-4 border-b border-zinc-100 dark:border-border/50">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  General Note
                </div>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {trade.notes}
                </p>
              </div>
            )}
            <NoteList tradeId={trade.id} />
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Performance Metrics */}
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
            <h2 className="text-base font-semibold text-foreground mb-4">
              Performance
            </h2>
            <div className="space-y-3">
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

              {/* Divider */}
              <div className="border-t border-border pt-3 space-y-3">
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
              </div>
            </div>
          </div>

          {/* Playbook & Psychology */}
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm">
            <h2 className="text-base font-semibold text-foreground mb-4">
              Playbook &amp; Psychology
            </h2>
            <div className="space-y-4">
              <div>
                <div className="text-xs text-muted-foreground mb-2">
                  Strategy / Setup
                </div>
                <InlinePlaybookField
                  playbookId={trade.playbook_id}
                  playbookName={trade.playbook_name}
                  onSave={handleSavePlaybook}
                />
              </div>
              <div className="relative">
                <div className="text-xs text-muted-foreground mb-2">Tags</div>
                <InlineTagsField
                  tagIds={trade.tags.map((t) => t.id)}
                  tags={trade.tags}
                  onSave={handleSaveTags}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

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
