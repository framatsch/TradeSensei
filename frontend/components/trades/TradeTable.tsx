/**
 * TradeTable — paginated, sortable, filterable table of trades with bulk selection.
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { useTrades } from "@/hooks/useTrades";
import type { TradeFilters, TradeSortConfig } from "@/hooks/useTrades";
import { TradeRow } from "./TradeRow";
import { Spinner } from "@/components/ui/Spinner";

interface Props {
  filters?: TradeFilters;
  sort?: TradeSortConfig;
  onSortChange?: (sort: TradeSortConfig) => void;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  limit?: number;
  onLimitChange?: (limit: number) => void;
}

type SortableColumn = "symbol" | "pnl" | "opened_at" | "closed_at";

const SORTABLE: SortableColumn[] = ["symbol", "pnl", "opened_at", "closed_at"];

const COLUMN_LABELS: Record<string, string> = {
  symbol: "Symbol",
  direction: "Direction",
  asset_class: "Asset Class",
  broker: "Broker",
  entry_price: "Entry Price",
  exit_price: "Exit Price",
  pnl: "PnL",
  opened_at: "Opened At",
  closed_at: "Closed At",
  tags: "Tags",
  notes: "Notes",
};

const ALL_COLUMNS = [
  "symbol",
  "direction",
  "asset_class",
  "broker",
  "entry_price",
  "exit_price",
  "pnl",
  "opened_at",
  "closed_at",
  "tags",
  "notes",
] as const;

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

function SortIcon({ column, sort }: { column: string; sort?: TradeSortConfig }) {
  if (sort?.sort_by !== column) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="w-3 h-3 text-slate-600 ml-1 inline"
      >
        <path d="M8 9l4-4 4 4M16 15l-4 4-4-4" />
      </svg>
    );
  }
  return sort.sort_dir === "asc" ? (
    <span className="ml-1 text-primary">▲</span>
  ) : (
    <span className="ml-1 text-primary">▼</span>
  );
}

export function TradeTable({
  filters,
  sort,
  onSortChange,
  selectedIds,
  onSelectionChange,
  limit = 20,
  onLimitChange,
}: Props) {
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const currentCursor = cursorStack[cursorStack.length - 1];

  // Reset cursor stack when filters, sort, or limit change
  const prevFiltersRef = useRef<TradeFilters | undefined>(undefined);
  const prevSortRef = useRef<TradeSortConfig | undefined>(undefined);
  const prevLimitRef = useRef<number>(limit);

  useEffect(() => {
    const filtersChanged =
      JSON.stringify(filters) !== JSON.stringify(prevFiltersRef.current);
    const sortChanged =
      JSON.stringify(sort) !== JSON.stringify(prevSortRef.current);
    const limitChanged = limit !== prevLimitRef.current;

    if (filtersChanged || sortChanged || limitChanged) {
      setCursorStack([null]);
      prevFiltersRef.current = filters;
      prevSortRef.current = sort;
      prevLimitRef.current = limit;
    }
  }, [filters, sort, limit]);

  const { data, isLoading, isError, error, refetch } = useTrades({
    cursor: currentCursor ?? undefined,
    limit,
    filters,
    sort,
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

  const handleSortClick = (column: SortableColumn) => {
    if (!onSortChange) return;
    if (sort?.sort_by === column) {
      onSortChange({
        sort_by: column,
        sort_dir: sort.sort_dir === "asc" ? "desc" : "asc",
      });
    } else {
      onSortChange({ sort_by: column, sort_dir: "desc" });
    }
  };

  const handleLimitChange = (newLimit: number) => {
    if (onLimitChange) onLimitChange(newLimit);
  };

  const trades = data?.items ?? [];

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return;
    if (checked) {
      onSelectionChange(new Set(trades.map((t) => t.id)));
    } else {
      onSelectionChange(new Set());
    }
  };

  const handleRowSelect = (id: string, checked: boolean) => {
    if (!onSelectionChange || !selectedIds) return;
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    onSelectionChange(next);
  };

  const allSelected = trades.length > 0 && trades.every((t) => selectedIds?.has(t.id));
  const someSelected = trades.some((t) => selectedIds?.has(t.id)) && !allSelected;

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
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Total displayed columns = 1 (checkbox) + ALL_COLUMNS.length
  const totalCols = ALL_COLUMNS.length + 1;

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border bg-background/50">
              {/* Select-all checkbox */}
              <th className="px-3 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="w-4 h-4 rounded border-border dark:border-border accent-primary cursor-pointer"
                  aria-label="Select all trades on this page"
                />
              </th>
              {ALL_COLUMNS.map((col) => {
                const isSortable = (SORTABLE as readonly string[]).includes(col);
                return (
                  <th
                    key={col}
                    className={`px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap ${
                      isSortable ? "cursor-pointer hover:text-foreground select-none" : ""
                    }`}
                    onClick={
                      isSortable
                        ? () => handleSortClick(col as SortableColumn)
                        : undefined
                    }
                  >
                    {COLUMN_LABELS[col]}
                    {isSortable && <SortIcon column={col} sort={sort} />}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td
                  colSpan={totalCols}
                  className="px-4 py-12 text-center text-muted-foreground"
                >
                  No trades found. Import trades to get started.
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <TradeRow
                  key={trade.id}
                  trade={trade}
                  isSelected={selectedIds?.has(trade.id) ?? false}
                  onSelect={handleRowSelect}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-border gap-4">
        <p className="text-xs text-muted-foreground shrink-0">
          {data?.total != null ? `${data.total} total trades` : ""}
        </p>

        <div className="flex items-center gap-4">
          {/* Page size selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground whitespace-nowrap">Rows per page</span>
            <select
              value={limit}
              onChange={(e) => handleLimitChange(Number(e.target.value))}
              className="px-2 py-1 text-sm bg-secondary border border-border dark:border-border text-muted-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          {/* Previous / Next */}
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={cursorStack.length <= 1}
              className="px-3 py-1.5 text-sm text-muted-foreground bg-secondary hover:bg-slate-200 dark:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors"
            >
              Previous
            </button>
            <button
              onClick={handleNext}
              disabled={!data?.next_cursor}
              className="px-3 py-1.5 text-sm text-muted-foreground bg-secondary hover:bg-slate-200 dark:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
