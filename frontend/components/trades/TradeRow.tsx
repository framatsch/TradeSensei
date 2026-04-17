/**
 * TradeRow — a single row in the trades table.
 * Includes tag chips, notes count badge, and link to trade detail.
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUp, ArrowDown } from "lucide-react";
import type { Trade } from "@/lib/types";
import { TagBadge } from "@/components/tags/TagBadge";
import { QuickNoteInput } from "@/components/notes/QuickNoteInput";

interface Props {
  trade: Trade;
  isSelected?: boolean;
  onSelect?: (id: string, checked: boolean) => void;
}

function formatPrice(value: string | null): string {
  if (value === null) return "—";
  return `$${parseFloat(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

function formatQuantity(value: string | number | null): string {
  if (value === null) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  return num.toLocaleString("en-US", {
    maximumFractionDigits: 3,
  });
}

function formatPnl(value: string | null): React.ReactElement {
  if (value === null) return <span className="text-muted-foreground">—</span>;
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
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
        isLong
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
          : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800"
      }`}
    >
      {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
      {direction}
    </span>
  );
}

export function TradeRow({ trade, isSelected = false, onSelect }: Props) {
  const notesCount = trade.trade_notes?.length ?? 0;
  const hasNotes = notesCount > 0;
  const [showQuickNote, setShowQuickNote] = useState(false);

  return (
    <>
    <tr className="border-b border-border hover:bg-secondary/30 transition-colors cursor-pointer">
      <td className="px-3 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect?.(trade.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          className="w-4 h-4 rounded border-border dark:border-border accent-primary cursor-pointer"
          aria-label={`Select trade ${trade.symbol}`}
        />
      </td>
      <td className="px-4 py-3 text-sm font-medium text-foreground">
        <Link
          href={`/dashboard/trades/${trade.id}`}
          className="hover:text-primary transition-colors inline-flex items-center gap-1.5"
          title={trade.id}
        >
          {trade.symbol}
        </Link>
      </td>
      <td className="px-4 py-3">
        <DirectionBadge direction={trade.direction} />
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {trade.asset_class}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {formatQuantity(trade.quantity)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {trade.account_name ?? <span className="text-muted-foreground">—</span>}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {formatPrice(trade.entry_price)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {formatPrice(trade.exit_price)}
      </td>
      <td className="px-4 py-3 text-sm">{formatPnl(trade.pnl)}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {formatDate(trade.opened_at)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
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
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setShowQuickNote((v) => !v);
          }}
          title={hasNotes ? `${notesCount} note${notesCount !== 1 ? "s" : ""} — click to add` : "Add note"}
          aria-label={hasNotes ? `${notesCount} notes` : "Add note"}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors border hover:border-primary hover:text-primary hover:bg-blue-900/20"
          style={hasNotes
            ? { background: "rgba(30,41,59,0.5)", color: "#94a3b8", borderColor: "#475569" }
            : { background: "transparent", color: "#475569", borderColor: "#334155" }
          }
        >
          <svg
            viewBox="0 0 24 24"
            fill={hasNotes ? "none" : "none"}
            stroke="currentColor"
            strokeWidth="2"
            className="w-3 h-3"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          {hasNotes ? notesCount : "+"}
        </button>
      </td>
    </tr>
    {showQuickNote && (
      <tr className="border-b border-border bg-zinc-50/30 dark:bg-zinc-900/30">
        <td colSpan={12} className="px-4 py-2">
          <QuickNoteInput
            tradeId={trade.id}
            onClose={() => setShowQuickNote(false)}
          />
        </td>
      </tr>
    )}
    </>
  );
}
