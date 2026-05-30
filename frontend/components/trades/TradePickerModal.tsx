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
 * TradePickerModal — searchable list of trades for selecting merge target or
 * execution reassignment target. Supports single-select and multi-select modes.
 */

"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { useTrades } from "@/hooks/useTrades";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import type { Trade } from "@/lib/types";

interface Props {
  /** Pre-filter to trades sharing this symbol (optional). */
  filterSymbol?: string;
  /** Pre-filter to trades sharing this account (optional). */
  filterAccountId?: string;
  /** IDs to exclude from the list (e.g. the source trade). */
  excludeIds?: string[];
  /** If true, only one trade can be selected. Defaults to false (multi-select). */
  singleSelect?: boolean;
  /** Label for the confirm button. Defaults to "Select". */
  confirmLabel?: string;
  onConfirm: (selectedTrades: Trade[]) => void;
  onClose: () => void;
}

function fmt(v: string | null): string {
  if (v === null) return "Open";
  const n = parseFloat(v);
  const prefix = n >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(n).toFixed(2)}`;
}

function fmtDate(v: string | null): string {
  if (!v) return "—";
  return new Date(v).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function TradePickerModal({
  filterSymbol,
  filterAccountId,
  excludeIds = [],
  singleSelect = false,
  confirmLabel = "Select",
  onConfirm,
  onClose,
}: Props) {
  const [search, setSearch] = useState(filterSymbol ?? "");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const showOpenTrades = useShowOpenTrades();

  const { data: page, isLoading } = useTrades({
    limit: 50,
    filters: {
      symbol: search.trim() || undefined,
      status: showOpenTrades ? undefined : "closed",
    },
  });

  const trades = (page?.items ?? []).filter((t) => !excludeIds.includes(t.id));

  const toggle = (trade: Trade) => {
    if (singleSelect) {
      setSelected(new Set([trade.id]));
      return;
    }
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(trade.id)) next.delete(trade.id);
      else next.add(trade.id);
      return next;
    });
  };

  const handleConfirm = () => {
    const picked = trades.filter((t) => selected.has(t.id));
    if (picked.length > 0) onConfirm(picked);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-card border border-border shadow-xl flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-base font-bold text-foreground mb-3">
            {singleSelect ? "Select Trade" : "Select Trades"}
          </h2>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              autoFocus
              type="text"
              className="w-full rounded-md border border-border bg-secondary pl-8 pr-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Search by symbol…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Trade list */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Loading…</span>
            </div>
          )}
          {!isLoading && trades.length === 0 && (
            <div className="py-10 text-center text-sm text-muted-foreground">
              No trades found
            </div>
          )}
          {!isLoading && trades.map((trade) => {
            const isSelected = selected.has(trade.id);
            const pnlNum = trade.pnl ? parseFloat(trade.pnl) : null;
            return (
              <button
                key={trade.id}
                type="button"
                onClick={() => toggle(trade)}
                className={`w-full flex items-center gap-3 px-5 py-3 text-left border-b border-border hover:bg-secondary transition-colors ${
                  isSelected ? "bg-[#6063dd]/5" : ""
                }`}
              >
                {/* Checkbox / radio */}
                <span
                  className={`flex h-4 w-4 items-center justify-center rounded${singleSelect ? "-full" : ""} border flex-shrink-0 transition-colors ${
                    isSelected
                      ? "bg-[#6063dd] border-[#6063dd]"
                      : "border-border"
                  }`}
                >
                  {isSelected && (
                    <svg viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.5" className="w-2.5 h-2.5">
                      {singleSelect ? (
                        <circle cx="6" cy="6" r="3" fill="white" stroke="none" />
                      ) : (
                        <polyline points="2,6 5,9 10,3" />
                      )}
                    </svg>
                  )}
                </span>

                {/* Trade info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground text-sm">{trade.symbol}</span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                        trade.is_combo
                          ? "bg-muted text-foreground border border-border"
                          : trade.direction === "LONG"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                          : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
                      }`}
                    >
                      {trade.is_combo ? "COMBO" : trade.direction}
                    </span>
                    <span className="text-xs text-muted-foreground">{trade.is_combo ? "COMBO" : (trade.asset_class ?? "—")}</span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Qty: {trade.quantity === null ? "—" : parseFloat(trade.quantity).toLocaleString()} · Opened: {fmtDate(trade.opened_at)}
                    {trade.account_name && ` · ${trade.account_name}`}
                  </div>
                </div>

                {/* P&L */}
                <span
                  className={`text-sm font-medium flex-shrink-0 ${
                    pnlNum === null
                      ? "text-amber-500"
                      : pnlNum >= 0
                      ? "text-emerald-500 dark:text-emerald-400"
                      : "text-red-500 dark:text-red-400"
                  }`}
                >
                  {fmt(trade.pnl)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {selected.size > 0
              ? `${selected.size} selected`
              : "No trades selected"}
          </span>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={selected.size === 0}
              className="rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
