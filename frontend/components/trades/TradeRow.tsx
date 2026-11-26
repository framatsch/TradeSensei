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

/**
 * TradeRow — a single row in the trades table.
 * Includes tag chips, notes count badge, and link to trade detail.
 */

"use client";


import { useState } from "react";
import Link from "next/link";
import { ArrowUp, ArrowDown, Split } from "lucide-react";
import type { Trade } from "@/lib/types";
import { TaxonomyBadge } from "@/components/trades/TaxonomyBadge";
import { QuickNoteInput } from "@/components/notes/QuickNoteInput";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { formatSplitRatio } from "@/lib/formatSplitRatio";

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
  const color = num >= 0 ? "text-success" : "text-danger";
  const prefix = num >= 0 ? "+" : "";
  return (
    <span className={`font-medium font-mono ${color}`}>
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
        isLong ? "badge-positive" : "badge-negative"
      }`}
    >
      {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
      {direction}
    </span>
  );
}

export function TradeRow({ trade, isSelected = false, onSelect }: Props) {
  const quickNotesEnabled = useFeatureFlag("enable_quick_notes");
  const notesCount = trade.trade_notes?.length ?? 0;
  const hasNotes = notesCount > 0;
  const [showQuickNote, setShowQuickNote] = useState(false);

  return (
    <>
    <tr className={`wl-row cursor-pointer ${isSelected ? "selected" : ""}`}>
      <td className="px-3 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onSelect?.(trade.id, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          className="w-4 h-4 rounded border-border accent-primary cursor-pointer"
          aria-label={`Select trade ${trade.symbol}`}
        />
      </td>
      <td className="px-4 py-3 text-sm font-medium text-foreground">
        <div className="inline-flex items-center gap-1.5">
          {isSelected && <span className="wl-focus-dot shrink-0" aria-hidden="true" />}
          <Link
            href={`/dashboard/trades/${trade.id}`}
            className="wl-ticker hover:text-primary transition-colors"
            title={trade.id}
          >
            {trade.symbol}
          </Link>
          {trade.corporate_action_impact && trade.corporate_action_impact.length > 0 && (
            <span
              className="inline-flex text-muted-foreground hover:text-foreground cursor-help"
              tabIndex={0}
              title={
                "Affected by a corporate action. Values may differ across the table, " +
                "the chart, and the as-traded price — open the trade for the " +
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
              <Split className="w-3.5 h-3.5" />
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {/* Direction is often meaningless for a combo trade — show only the COMBO
            indicator in the asset-class column below instead of a LONG/SHORT badge. */}
        {!trade.is_combo && <DirectionBadge direction={trade.direction} />}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {trade.is_combo ? "COMBO" : trade.asset_class}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
        {formatQuantity(trade.quantity)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {trade.account_name ?? <span className="text-muted-foreground">—</span>}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
        {formatPrice(trade.entry_price)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
        {formatPrice(trade.exit_price)}
      </td>
      <td className="px-4 py-3 text-sm font-mono">{formatPnl(trade.pnl)}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
        {formatDate(trade.opened_at)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
        {formatDate(trade.closed_at)}
      </td>
      <td className="px-4 py-3">
          <div className="flex items-center gap-1.5 flex-wrap max-w-48">
          {trade.taxonomies?.map((taxonomy) => (
            <TaxonomyBadge key={taxonomy.id} taxonomy={taxonomy} />
          ))}
        </div>
      </td>
      {quickNotesEnabled && (
        <td className="px-4 py-3">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowQuickNote((v) => !v);
            }}
            title={hasNotes ? `${notesCount} note${notesCount !== 1 ? "s" : ""} — click to add` : "Add note"}
            aria-label={hasNotes ? `${notesCount} notes` : "Add note"}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium font-mono transition-colors border hover:border-primary hover:text-primary hover:bg-primary/10 ${
              hasNotes
                ? "bg-secondary text-muted-foreground border-border"
                : "bg-transparent text-muted-foreground/70 border-border/60"
            }`}
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
      )}
    </tr>
    {quickNotesEnabled && showQuickNote && (
      <tr className="border-b border-border bg-secondary">
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
