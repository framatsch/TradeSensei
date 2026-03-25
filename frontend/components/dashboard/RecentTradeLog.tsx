/**
 * RecentTradeLog — Minimalist table of the 10 most recent closed trades.
 *
 * Uses the .radiant-table utility for a clean, no-vertical-lines look.
 * Links to /dashboard/trades for the full trade list.
 */

"use client";

import Link from "next/link";
import { ArrowRight, ArrowUp, ArrowDown } from "lucide-react";
import { useTrades } from "@/hooks/useTrades";
import { Spinner } from "@/components/ui/Spinner";
import type { Trade } from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(iso));
}

function formatPnl(pnl: string | null): { text: string; cls: string } {
  if (!pnl) return { text: "—", cls: "text-muted-foreground" };
  const num = parseFloat(pnl);
  const abs = Math.abs(num);
  const prefix = num >= 0 ? "+" : "−";
  let text: string;
  if (abs >= 1_000_000) text = `${prefix}$${(abs / 1_000_000).toFixed(2)}M`;
  else if (abs >= 1_000) text = `${prefix}$${(abs / 1_000).toFixed(1)}K`;
  else text = `${prefix}$${abs.toFixed(2)}`;
  return {
    text,
    cls: num > 0 ? "text-success" : num < 0 ? "text-danger" : "text-muted-foreground",
  };
}

// ─── Row ──────────────────────────────────────────────────────────────────────

function TradeRow({ trade }: { trade: Trade }) {
  const pnl = formatPnl(trade.pnl);
  const isLong = trade.direction === "LONG";

  return (
    <tr className="group border-b border-border hover:bg-muted/40 transition-colors">
      {/* Date */}
      <td className="py-3 pr-4 text-xs font-mono text-muted-foreground whitespace-nowrap">
        {formatDate(trade.closed_at)}
      </td>

      {/* Symbol */}
      <td className="py-3 pr-4">
        <span className="text-sm font-semibold tracking-wide text-foreground">
          {trade.symbol}
        </span>
      </td>

      {/* Direction badge */}
      <td className="py-3 pr-4">
        <span
          className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full ${
            isLong
              ? "bg-success/10 text-success"
              : "bg-danger/10 text-danger"
          }`}
        >
          {isLong ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
          {trade.direction}
        </span>
      </td>

      {/* Setup / Playbook */}
      <td className="py-3 pr-4 hidden sm:table-cell">
        <span className="text-xs font-mono text-muted-foreground">
          {trade.playbook_name ?? (
            <span className="opacity-40">—</span>
          )}
        </span>
      </td>

      {/* Net Profit */}
      <td className="py-3 text-right">
        <span className={`text-sm font-semibold font-mono tabular-nums ${pnl.cls}`}>
          {pnl.text}
        </span>
      </td>
    </tr>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function RecentTradeLog() {
  const { data, isLoading } = useTrades({
    limit: 10,
    filters: { status: "closed" },
    sort: { sort_by: "closed_at", sort_dir: "desc" },
  });

  const trades = data?.items ?? [];

  return (
    <div className="radiant-card light-edge noise-overlay">
      {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            Recent Trades
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Last 10 closed positions
          </p>
        </div>
        <Link
          href="/dashboard/trades"
          className="btn-ghost flex items-center gap-1.5 text-xs"
        >
          View all
          <ArrowRight size={13} />
        </Link>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner />
          </div>
        ) : trades.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-muted-foreground">No closed trades yet</p>
            <Link
              href="/dashboard/import"
              className="mt-3 text-xs text-primary hover:underline"
            >
              Import your first trades →
            </Link>
          </div>
        ) : (
          <table className="radiant-table w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="pb-2 pr-4 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Date
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Symbol
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Side
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-bold uppercase tracking-widest text-muted-foreground hidden sm:table-cell">
                  Setup
                </th>
                <th className="pb-2 text-right text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Net P&amp;L
                </th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
