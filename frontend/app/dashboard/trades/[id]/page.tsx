/**
 * Trade detail page — full trade info + notes panel.
 */

"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useTrade } from "@/hooks/useTrade";
import { NoteList } from "@/components/notes/NoteList";
import { TagBadge } from "@/components/tags/TagBadge";
import { Spinner } from "@/components/ui/Spinner";

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-4 py-3 border-b border-slate-700/50 last:border-0">
      <dt className="w-40 shrink-0 text-sm text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-200">{children}</dd>
    </div>
  );
}

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

function PnlDisplay({ value }: { value: string | null }) {
  if (value === null) return <span className="text-slate-500">—</span>;
  const num = parseFloat(value);
  const color = num >= 0 ? "text-emerald-400" : "text-red-400";
  const prefix = num >= 0 ? "+" : "";
  return (
    <span className={`font-semibold ${color}`}>
      {prefix}${Math.abs(num).toFixed(2)}
    </span>
  );
}

export default function TradeDetailPage() {
  const params = useParams();
  const tradeId = typeof params.id === "string" ? params.id : "";
  const { data: trade, isLoading, isError, error } = useTrade(tradeId);

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

  return (
    <div className="max-w-4xl space-y-6">
      {/* Back link */}
      <div>
        <Link
          href="/dashboard/trades"
          className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-100 transition-colors"
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
      <div className="flex items-center gap-4 flex-wrap">
        <h1 className="text-2xl font-bold text-slate-100">{trade.symbol}</h1>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium ${
            isLong
              ? "bg-emerald-900/50 text-emerald-400 border border-emerald-800"
              : "bg-red-900/50 text-red-400 border border-red-800"
          }`}
        >
          {trade.direction}
        </span>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded text-sm font-medium bg-slate-700 text-slate-300 border border-slate-600">
          {trade.asset_class}
        </span>
        {trade.tags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {trade.tags.map((tag) => (
              <TagBadge key={tag.id} tag={tag} />
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trade details */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">
            Trade Details
          </h2>
          <dl>
            <DetailRow label="Symbol">{trade.symbol}</DetailRow>
            <DetailRow label="Direction">{trade.direction}</DetailRow>
            <DetailRow label="Asset Class">{trade.asset_class}</DetailRow>
            <DetailRow label="Quantity">{trade.quantity}</DetailRow>
            <DetailRow label="Entry Price">
              {formatPrice(trade.entry_price)}
            </DetailRow>
            <DetailRow label="Exit Price">
              {formatPrice(trade.exit_price)}
            </DetailRow>
            <DetailRow label="Stop Loss">
              {formatPrice(trade.stop_loss)}
            </DetailRow>
            <DetailRow label="Take Profit">
              {formatPrice(trade.take_profit)}
            </DetailRow>
            <DetailRow label="PnL">
              <PnlDisplay value={trade.pnl} />
            </DetailRow>
            <DetailRow label="Commission">
              {formatPrice(trade.commission)}
            </DetailRow>
            <DetailRow label="Opened At">
              {formatDate(trade.opened_at)}
            </DetailRow>
            <DetailRow label="Closed At">
              {formatDate(trade.closed_at)}
            </DetailRow>
            {trade.playbook_id && (
              <DetailRow label="Playbook">
                <span className="text-blue-400">{trade.playbook_id}</span>
              </DetailRow>
            )}
            {trade.notes && (
              <DetailRow label="General Notes">{trade.notes}</DetailRow>
            )}
          </dl>
        </div>

        {/* Tags panel */}
        {trade.tags.length > 0 && (
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 h-fit">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">Tags</h2>
            <div className="flex flex-wrap gap-2">
              {trade.tags.map((tag) => (
                <TagBadge key={tag.id} tag={tag} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Notes section */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">
          Trade Notes
          {trade.trade_notes.length > 0 && (
            <span className="ml-2 text-xs font-normal text-slate-500">
              ({trade.trade_notes.length})
            </span>
          )}
        </h2>
        <NoteList tradeId={trade.id} />
      </div>
    </div>
  );
}
