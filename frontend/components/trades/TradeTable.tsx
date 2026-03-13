/**
 * TradeTable — paginated table of trades.
 */

"use client";

import { useState } from "react";
import { useTrades } from "@/hooks/useTrades";
import { TradeRow } from "./TradeRow";
import { Spinner } from "@/components/ui/Spinner";

const COLUMNS = [
  "Symbol",
  "Direction",
  "Asset Class",
  "Entry Price",
  "Exit Price",
  "PnL",
  "Opened At",
  "Closed At",
  "Tags",
  "Notes",
];

export function TradeTable() {
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const currentCursor = cursorStack[cursorStack.length - 1];

  const { data, isLoading, isError, error, refetch } = useTrades({
    cursor: currentCursor ?? undefined,
    limit: 20,
  });

  const handleNext = () => {
    if (data?.next_cursor) {
      setCursorStack((prev) => [...prev, data.next_cursor]);
    }
  };

  const handlePrev = () => {
    if (cursorStack.length > 1) {
      setCursorStack((prev) => prev.slice(0, -1));
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-red-400 font-medium mb-2">Failed to load trades.</p>
        <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const trades = data?.items ?? [];

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-900/50">
              {COLUMNS.map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td
                  colSpan={COLUMNS.length}
                  className="px-4 py-12 text-center text-slate-500"
                >
                  No trades found. Import trades to get started.
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <TradeRow key={trade.id} trade={trade} />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
        <p className="text-xs text-slate-500">
          {data?.total != null ? `${data.total} total trades` : ""}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrev}
            disabled={cursorStack.length <= 1}
            className="px-3 py-1.5 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            Previous
          </button>
          <button
            onClick={handleNext}
            disabled={!data?.next_cursor}
            className="px-3 py-1.5 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
