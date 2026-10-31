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
 * TradeTable — paginated, sortable, filterable table of trades with bulk selection.
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { useTrades } from "@/hooks/useTrades";
import type { TradeFilters, TradeSortConfig } from "@/hooks/useTrades";
import { TradeRow } from "./TradeRow";
import { TradeCard } from "./TradeCard";
import { Spinner } from "@/components/ui/Spinner";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import {
  isSameQuery,
  readTradeListContext,
  upsertPage,
  writeTradeListContext,
  type TradeListContext,
} from "@/lib/tradeListContext";

interface Props {
  portfolioId?: string;
  filters?: TradeFilters;
  sort?: TradeSortConfig;
  onSortChange?: (sort: TradeSortConfig) => void;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  /** Fired whenever selection changes, with full Trade objects for the selected IDs in the current page. */
  onSelectedTradesChange?: (trades: import("@/lib/types").Trade[]) => void;
  limit?: number;
  onLimitChange?: (limit: number) => void;
  listQuery?: string;
  viewName?: string | null;
}

type SortableColumn = "symbol" | "pnl" | "opened_at" | "closed_at";

const SORTABLE: SortableColumn[] = ["symbol", "pnl", "opened_at", "closed_at"];

const COLUMN_LABELS: Record<string, string> = {
  symbol: "Symbol",
  direction: "Direction",
  asset_class: "Asset Class",
  quantity: "Qty",
  broker: "Broker",
  entry_price: "Entry Price",
  exit_price: "Exit Price",
  pnl: "PnL",
  opened_at: "Opened At",
  closed_at: "Closed At",
  tags: "Tags",
  notes: "Notes",
};

const BASE_COLUMNS = [
  "symbol",
  "direction",
  "asset_class",
  "quantity",
  "broker",
  "entry_price",
  "exit_price",
  "pnl",
  "opened_at",
  "closed_at",
  "tags",
] as const;

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;

const SORT_OPTIONS: { label: string; sort: TradeSortConfig }[] = [
  { label: "Opened: newest", sort: { sort_by: "opened_at", sort_dir: "desc" } },
  { label: "Opened: oldest", sort: { sort_by: "opened_at", sort_dir: "asc" } },
  { label: "Closed: newest", sort: { sort_by: "closed_at", sort_dir: "desc" } },
  { label: "Closed: oldest", sort: { sort_by: "closed_at", sort_dir: "asc" } },
  { label: "P&L: highest", sort: { sort_by: "pnl", sort_dir: "desc" } },
  { label: "P&L: lowest", sort: { sort_by: "pnl", sort_dir: "asc" } },
  { label: "Symbol: A → Z", sort: { sort_by: "symbol", sort_dir: "asc" } },
  { label: "Symbol: Z → A", sort: { sort_by: "symbol", sort_dir: "desc" } },
];

interface PaginationState {
  queryKey: string;
  cursors: (string | null)[];
}

function SortIcon({ column, sort }: { column: string; sort?: TradeSortConfig }) {
  if (sort?.sort_by !== column) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="w-3 h-3 text-zinc-600 ml-1 inline"
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
  portfolioId,
  filters,
  sort,
  onSortChange,
  selectedIds,
  onSelectionChange,
  onSelectedTradesChange,
  limit = 25,
  onLimitChange,
  listQuery = "",
  viewName = null,
}: Props) {
  const quickNotesEnabled = useFeatureFlag("enable_quick_notes");
  const allColumns = quickNotesEnabled ? [...BASE_COLUMNS, "notes"] : [...BASE_COLUMNS];

  const [selectionMode, setSelectionMode] = useState(false);
  const queryKey = JSON.stringify([portfolioId, filters, sort, limit]);
  const [pagination, setPagination] = useState<PaginationState>(() => ({ queryKey, cursors: [null] }));
  const queryIsCurrent = pagination.queryKey === queryKey;
  // Never send an old query's cursor, including the first render after a query change.
  const cursorStack = queryIsCurrent ? pagination.cursors : [null];
  const currentCursor = cursorStack[cursorStack.length - 1];
  const contextRef = useRef<TradeListContext | null>(null);

  // Reset during render so React retries before committing an old cursor's effects.
  if (!queryIsCurrent) {
    setPagination({ queryKey, cursors: [null] });
  }

  const { data, isLoading, isError, error, refetch, isPlaceholderData } = useTrades({
    portfolioId,
    cursor: currentCursor ?? undefined,
    limit,
    filters,
    sort,
  });

  useEffect(() => {
    if (!portfolioId || !queryIsCurrent || !data || isLoading || isError || isPlaceholderData) return;

    const freshContext: TradeListContext = {
      portfolioId,
      filters: filters ?? {},
      sort: sort ?? {},
      limit,
      listQuery,
      viewName,
      total: data.total ?? null,
      pages: [],
    };
    const stored = readTradeListContext();
    const previous = stored && isSameQuery(stored, freshContext)
      ? stored
      : contextRef.current && isSameQuery(contextRef.current, freshContext)
      ? contextRef.current
      : freshContext;
    const pageIndex = cursorStack.length - 1;

    // Missing or invalidated predecessor pages must never create a gap in navigation.
    if (pageIndex > 0 && previous.pages[pageIndex - 1]?.nextCursor !== currentCursor) return;

    const context = upsertPage(
      { ...previous, listQuery, viewName, total: data.total ?? previous.total },
      pageIndex,
      { cursor: currentCursor ?? null, ids: data.items.map((trade) => trade.id), nextCursor: data.next_cursor ?? null },
    );
    contextRef.current = context;
    writeTradeListContext(context);
  }, [portfolioId, filters, sort, limit, listQuery, viewName, data, isLoading, isError, isPlaceholderData, queryIsCurrent, cursorStack.length, currentCursor]);

  const handleNext = () => {
    if (data?.next_cursor) {
      setPagination({ queryKey, cursors: [...cursorStack, data.next_cursor] });
    }
  };

  const handlePrev = () => {
    if (cursorStack.length > 1) {
      setPagination({ queryKey, cursors: cursorStack.slice(0, -1) });
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
    const nextIds = checked ? new Set(trades.map((t) => t.id)) : new Set<string>();
    onSelectionChange(nextIds);
    onSelectedTradesChange?.(checked ? [...trades] : []);
  };

  const handleRowSelect = (id: string, checked: boolean) => {
    if (!onSelectionChange || !selectedIds) return;
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    onSelectionChange(next);
    onSelectedTradesChange?.(trades.filter((t) => next.has(t.id)));
  };

  const allSelected = trades.length > 0 && trades.every((t) => selectedIds?.has(t.id));
  const someSelected = trades.some((t) => selectedIds?.has(t.id)) && !allSelected;
  const pageSizeOptions = Array.from(new Set([limit, ...PAGE_SIZE_OPTIONS])).sort((a, b) => a - b);

  if (isLoading && portfolioId) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-danger font-medium mb-2">Failed to load trades.</p>
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="btn-primary"
        >
          Retry
        </button>
      </div>
    );
  }

  // Total displayed columns = 1 (checkbox) + allColumns.length
  const totalCols = allColumns.length + 1;

  return (
    <div className="solid-card">
      <div className="flex min-h-14 items-center justify-between gap-3 border-b border-border p-3 lg:hidden">
        {selectionMode ? (
          <label className="flex min-h-10 items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={allSelected}
              ref={(element) => { if (element) element.indeterminate = someSelected; }}
              onChange={(event) => handleSelectAll(event.target.checked)}
              className="h-5 w-5 rounded border-border accent-primary focus-visible:ring-2 focus-visible:ring-ring"
            />
            Select all on page
          </label>
        ) : (
          <select
            aria-label="Sort trades"
            value={`${sort?.sort_by ?? "opened_at"}:${sort?.sort_dir ?? "desc"}`}
            onChange={(event) => {
              const option = SORT_OPTIONS.find(({ sort: optionSort }) => `${optionSort.sort_by}:${optionSort.sort_dir}` === event.target.value);
              if (option) onSortChange?.(option.sort);
            }}
            className="min-h-10 min-w-0 flex-1 rounded-md border border-border bg-secondary px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.label} value={`${option.sort.sort_by}:${option.sort.sort_dir}`}>{option.label}</option>
            ))}
          </select>
        )}
        <button
          type="button"
          className="btn-ghost min-h-10 shrink-0 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => {
            if (selectionMode) {
              onSelectionChange?.(new Set());
              onSelectedTradesChange?.([]);
            }
            setSelectionMode((value) => !value);
          }}
        >
          {selectionMode ? "Done" : "Select"}
        </button>
      </div>

      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              {/* Select-all checkbox */}
              <th className="px-3 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="w-4 h-4 rounded border-border accent-primary cursor-pointer"
                  aria-label="Select all trades on this page"
                />
              </th>
              {allColumns.map((col) => {
                const isSortable = (SORTABLE as readonly string[]).includes(col);
                return (
                  <th
                    key={col}
                    className={`px-4 py-3 text-[10px] font-bold text-muted-foreground uppercase tracking-widest whitespace-nowrap ${
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

      <div className="space-y-3 p-3 lg:hidden" data-testid="trade-card-list">
        {trades.length === 0 ? (
          <p className="px-1 py-12 text-center text-sm text-muted-foreground">No trades found. Import trades to get started.</p>
        ) : trades.map((trade) => (
          <TradeCard
            key={trade.id}
            trade={trade}
            selectionMode={selectionMode}
            isSelected={selectedIds?.has(trade.id) ?? false}
            onSelect={handleRowSelect}
          />
        ))}
      </div>

      {/* Pagination controls */}
      <div className="hidden items-center justify-between px-4 py-3 border-t border-border gap-4 lg:flex">
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
              className="px-2 py-1 text-sm bg-secondary border border-border text-muted-foreground rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          {/* Previous / Next */}
          {(cursorStack.length > 1 || data?.next_cursor) && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground mr-2">Page {cursorStack.length}</span>
              <button
                onClick={handlePrev}
                disabled={cursorStack.length <= 1}
                className="px-3 py-1.5 text-sm text-muted-foreground bg-secondary hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors border border-border"
              >
                Previous
              </button>
              <button
                onClick={handleNext}
                disabled={!data?.next_cursor}
                className="px-3 py-1.5 text-sm text-muted-foreground bg-secondary hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors border border-border"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="space-y-2 border-t border-border p-3 lg:hidden">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            {data?.total != null && <><span className="font-mono">{data.total}</span> total trades</>}
          </p>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Rows
            <select
              value={limit}
              onChange={(event) => handleLimitChange(Number(event.target.value))}
              className="min-h-10 rounded-md border border-border bg-secondary px-2 font-mono text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {pageSizeOptions.map((size) => <option key={size} value={size}>{size}</option>)}
            </select>
          </label>
        </div>
        <div className="flex items-center justify-center gap-3">
          <button type="button" onClick={handlePrev} disabled={cursorStack.length <= 1} className="btn-ghost min-h-10 px-3 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">‹ Prev</button>
          <span className="text-xs text-muted-foreground">Page <span className="font-mono">{cursorStack.length}</span></span>
          <button type="button" onClick={handleNext} disabled={!data?.next_cursor} className="btn-ghost min-h-10 px-3 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Next ›</button>
        </div>
      </div>
    </div>
  );
}
