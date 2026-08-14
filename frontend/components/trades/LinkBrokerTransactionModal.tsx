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
 * LinkBrokerTransactionModal — pick a broker raw transaction to link to a
 * manual execution leg.
 *
 * Lists BRTs for the execution's account, pre-filtered by the execution's
 * symbol. The user can toggle the symbol filter off, search by raw-ID
 * substring, and confirm. On 409 (BRT already linked elsewhere), the
 * conflict reason is shown inline.
 */

"use client";

import { useMemo, useState } from "react";
import { Loader2, Search } from "lucide-react";
import type { LogicalExecution } from "@/lib/types";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useBrokerTransactions, useLinkBrokerTransaction } from "@/hooks/useExecutions";
import { extractApiError } from "@/lib/apiErrors";

interface Props {
  execution: LogicalExecution;
  tradeId: string;
  onClose: () => void;
}

function fmtDate(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function LinkBrokerTransactionModal({ execution, tradeId, onClose }: Props) {
  const { activePortfolioId } = useActivePortfolio();
  const accountId = execution.account_id;
  const [symbolFilterOn, setSymbolFilterOn] = useState(true);
  const [idSearch, setIdSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: brts, isLoading, isError, refetch } = useBrokerTransactions(
    activePortfolioId,
    accountId,
    symbolFilterOn ? execution.symbol : null,
  );
  const linkMutation = useLinkBrokerTransaction();

  const filtered = useMemo(() => {
    if (!brts) return [];
    const term = idSearch.trim().toLowerCase();
    const candidates = brts.filter((b) => !b.suppressed);
    if (!term) return candidates;
    return candidates.filter((b) => b.id.toLowerCase().includes(term));
  }, [brts, idSearch]);

  const handleConfirm = () => {
    if (!selectedId || !activePortfolioId) return;
    setErrorMsg(null);
    linkMutation.mutate(
      {
        executionId: execution.id,
        tradeId,
        portfolioId: activePortfolioId,
        rawTransactionId: selectedId,
      },
      {
        onSuccess: () => onClose(),
        onError: (err) => setErrorMsg(extractApiError(err, "Failed to link broker transaction.")),
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl solid-card p-5 shadow-2xl flex flex-col max-h-[80vh]">
        <h3 className="text-sm font-semibold text-foreground">Link broker transaction</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Link this manual leg to the broker fill it replaces. The broker fill will be
          suppressed on future imports so it does not duplicate this leg.
        </p>

        {/* Filters */}
        <div className="mt-3 flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={symbolFilterOn}
              onChange={(e) => setSymbolFilterOn(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-border accent-primary"
            />
            Only symbol {execution.symbol}
          </label>
          <div className="relative flex-1">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={idSearch}
              onChange={(e) => setIdSearch(e.target.value)}
              placeholder="Search by transaction ID…"
              aria-label="Search by transaction ID"
              className="w-full rounded-md border border-border bg-secondary pl-8 pr-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* List */}
        <div className="mt-3 flex-1 overflow-y-auto border border-border rounded-md min-h-[12rem]">
          {isLoading && (
            <div className="flex items-center justify-center py-10 text-muted-foreground gap-2">
              <Loader2 size={15} className="animate-spin" />
              <span className="text-xs">Loading broker transactions…</span>
            </div>
          )}
          {isError && (
            <div className="flex flex-col items-center justify-center gap-2 py-10">
              <span className="text-xs text-destructive">Could not load broker transactions.</span>
              <button onClick={() => refetch()} className="text-xs text-primary underline">Retry</button>
            </div>
          )}
          {!isLoading && !isError && filtered.length === 0 && (
            <div className="py-10 text-center text-xs text-muted-foreground">
              No matching broker transactions found.
            </div>
          )}
          {!isLoading && !isError && filtered.length > 0 && (
            <ul className="divide-y divide-border">
              {filtered.map((b) => (
                <li key={b.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(b.id)}
                    aria-label={`Select broker transaction ${b.id}`}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors ${
                      selectedId === b.id ? "bg-primary/10 border-l-2 border-primary" : "hover:bg-muted"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-foreground">{b.symbol}</span>
                      <span className="text-muted-foreground">{fmtDate(b.executed_at)}</span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between gap-2 text-muted-foreground">
                      <span className="font-mono">
                        {b.direction} {parseFloat(b.quantity).toLocaleString("en-US", { maximumFractionDigits: 4 })} @{" "}
                        {parseFloat(b.price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                      </span>
                      <span className="font-mono text-[10px] truncate max-w-[14rem]" title={b.id}>
                        {b.id}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {errorMsg && (
          <p className="mt-3 text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
            {errorMsg}
          </p>
        )}

        {/* Actions */}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={linkMutation.isPending}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-secondary disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!selectedId || linkMutation.isPending}
            className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {linkMutation.isPending ? "Linking…" : "Link transaction"}
          </button>
        </div>
      </div>
    </div>
  );
}
