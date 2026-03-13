/**
 * TradeRow — a single row in the trades table.
 * Includes tag chips, notes count badge, and link to trade detail.
 */

"use client";

import Link from "next/link";
import type { Trade } from "@/lib/types";
import { TagBadge } from "@/components/tags/TagBadge";

interface Props {
  trade: Trade;
}

function formatPrice(value: string | null): string {
  if (value === null) return "—";
  return `$${parseFloat(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

function formatPnl(value: string | null): React.ReactElement {
  if (value === null) return <span className="text-slate-500">—</span>;
  const num = parseFloat(value);
  const color = num >= 0 ? "text-emerald-400" : "text-red-400";
  const prefix = num >= 0 ? "+" : "";
  return (
    <span className={`font-medium ${color}`}>
      {prefix}${Math.abs(num).toFixed(2)}
    </span>
  );
}

function formatDate(value: string | null): string {
  if (value === null) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function DirectionBadge({ direction }: { direction: string }) {
  const isLong = direction === "LONG";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        isLong
          ? "bg-emerald-900/50 text-emerald-400 border border-emerald-800"
          : "bg-red-900/50 text-red-400 border border-red-800"
      }`}
    >
      {direction}
    </span>
  );
}

export function TradeRow({ trade }: Props) {
  const notesCount = trade.trade_notes?.length ?? 0;

  return (
    <tr className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors cursor-pointer">
      <td className="px-4 py-3 text-sm font-medium text-slate-100">
        <Link
          href={`/dashboard/trades/${trade.id}`}
          className="hover:text-blue-400 transition-colors"
        >
          {trade.symbol}
        </Link>
      </td>
      <td className="px-4 py-3">
        <DirectionBadge direction={trade.direction} />
      </td>
      <td className="px-4 py-3 text-sm text-slate-400">
        {trade.asset_class}
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {formatPrice(trade.entry_price)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {formatPrice(trade.exit_price)}
      </td>
      <td className="px-4 py-3 text-sm">{formatPnl(trade.pnl)}</td>
      <td className="px-4 py-3 text-sm text-slate-400">
        {formatDate(trade.opened_at)}
      </td>
      <td className="px-4 py-3 text-sm text-slate-400">
        {formatDate(trade.closed_at)}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 flex-wrap max-w-48">
          {trade.tags?.map((tag) => (
            <TagBadge key={tag.id} tag={tag} />
          ))}
        </div>
      </td>
      <td className="px-4 py-3">
        {notesCount > 0 ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-300 border border-slate-600">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-3 h-3"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            {notesCount}
          </span>
        ) : (
          <span className="text-slate-600 text-xs">—</span>
        )}
      </td>
    </tr>
  );
}
