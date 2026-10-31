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

import { useState } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, MessageSquare, Split } from "lucide-react";
import { QuickNoteInput } from "@/components/notes/QuickNoteInput";
import { TaxonomyBadge } from "@/components/trades/TaxonomyBadge";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { formatSplitRatio } from "@/lib/formatSplitRatio";
import type { Trade } from "@/lib/types";

interface Props {
  trade: Trade;
  selectionMode?: boolean;
  isSelected?: boolean;
  onSelect?: (id: string, checked: boolean) => void;
}

function formatPrice(value: string | null): string {
  if (value === null) return "—";
  return `$${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}`;
}

function formatDate(value: string | null): string {
  if (value === null) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function TradeCard({ trade, selectionMode = false, isSelected = false, onSelect }: Props) {
  const quickNotesEnabled = useFeatureFlag("enable_quick_notes");
  const [showQuickNote, setShowQuickNote] = useState(false);
  const notesCount = trade.trade_notes?.length ?? 0;
  const pnl = trade.pnl === null ? null : Number(trade.pnl);
  const isLong = trade.direction === "LONG";

  return (
    <div className="min-w-0">
      <article className={`solid-card p-4 ${isSelected ? "ring-2 ring-primary" : ""}`}>
        <div className="flex items-start gap-3">
          {selectionMode && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(event) => onSelect?.(trade.id, event.target.checked)}
              className="relative z-10 mt-1 h-5 w-5 shrink-0 rounded border-border accent-primary focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Select trade ${trade.symbol}`}
            />
          )}
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                <Link
                  href={`/dashboard/trades/${trade.id}`}
                  aria-label={trade.symbol}
                  onClick={(event) => {
                    if (selectionMode) {
                      event.preventDefault();
                      onSelect?.(trade.id, !isSelected);
                    }
                  }}
                  className="break-all text-sm font-semibold text-foreground after:absolute after:inset-0 after:rounded-xl hover:text-foreground focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-ring"
                >
                  {trade.symbol}
                </Link>
                {!!trade.corporate_action_impact?.length && (
                  <span
                    aria-label="Affected by a corporate action"
                    title={trade.corporate_action_impact.map((action) => `Split ${formatSplitRatio(action.ratio)} on ${action.date}`).join("\n")}
                    className="text-muted-foreground"
                  >
                    <Split className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                )}
                {!trade.is_combo && (
                  <span className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${isLong ? "bg-[color-mix(in_srgb,var(--success)_12%,transparent)] text-success" : "bg-[color-mix(in_srgb,var(--danger)_12%,transparent)] text-danger"}`}>
                    {isLong ? <ArrowUp className="h-3 w-3" aria-hidden="true" /> : <ArrowDown className="h-3 w-3" aria-hidden="true" />}
                    {trade.direction}
                  </span>
                )}
                <span className="text-[10px] font-medium text-muted-foreground">{trade.is_combo ? "COMBO" : trade.asset_class}</span>
                {!trade.closed_at && <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">Open</span>}
              </div>
              <span className={`shrink-0 font-mono text-sm font-semibold ${pnl === null ? "text-muted-foreground" : pnl >= 0 ? "text-success" : "text-danger"}`}>
                {pnl === null ? "—" : `${pnl >= 0 ? "+" : "-"}$${Math.abs(pnl).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              </span>
            </div>
            <p className="font-mono text-xs text-muted-foreground">
              {trade.quantity === null ? "—" : Number(trade.quantity).toLocaleString("en-US", { maximumFractionDigits: 3 })} @ {formatPrice(trade.entry_price)} → {formatPrice(trade.exit_price)}
            </p>
            <p className="break-words text-xs text-muted-foreground">
              <span className="font-mono">{formatDate(trade.opened_at)} → {formatDate(trade.closed_at)}</span> · {trade.account_name ?? "—"}
            </p>
            {(!!trade.taxonomies?.length || quickNotesEnabled) && (
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 flex-wrap gap-1.5">
                  {trade.taxonomies?.map((taxonomy) => <TaxonomyBadge key={taxonomy.id} taxonomy={taxonomy} />)}
                </div>
                {quickNotesEnabled && (
                  <button
                    type="button"
                    aria-label={notesCount > 0 ? `${notesCount} notes` : "Add note"}
                    aria-expanded={showQuickNote}
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setShowQuickNote((value) => !value);
                    }}
                    className="relative z-10 inline-flex min-h-10 min-w-10 shrink-0 items-center justify-center gap-1 rounded-md border border-border px-2 font-mono text-xs text-muted-foreground hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
                    {notesCount > 0 ? notesCount : "+"}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </article>
      {quickNotesEnabled && showQuickNote && (
        <div className="px-2 pt-2">
          <QuickNoteInput tradeId={trade.id} onClose={() => setShowQuickNote(false)} />
        </div>
      )}
    </div>
  );
}
