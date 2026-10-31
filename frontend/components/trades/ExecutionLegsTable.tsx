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
 * ExecutionLegsTable — collapsible table showing all execution legs for a trade.
 *
 * Task 8.4: hide deleted executions by default; add "Show deleted" toggle.
 * Deleted rows render at 50% opacity with a [Restore] button (ExecutionRow).
 * Task 8.9: open SplitExecutionModal from the ExecutionRow context menu.
 */

"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, Plus, Loader2, ArrowUpDown, ArrowUp, ArrowDown, Split } from "lucide-react";
import { useTradeExecutions, useReassignExecution, useDetachExecution } from "@/hooks/useExecutions";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { formatSplitRatio } from "@/lib/formatSplitRatio";
import { ExecutionRow } from "./ExecutionRow";
import { ExecutionLegCard } from "./ExecutionLegCard";
import { AddExecutionModal } from "./AddExecutionModal";
import { TradePickerModal } from "./TradePickerModal";
import { SplitExecutionModal } from "./SplitExecutionModal";
import { LinkBrokerTransactionModal } from "./LinkBrokerTransactionModal";
import type { LogicalExecution, Trade } from "@/lib/types";

interface Props {
  tradeId: string;
  trade: Trade;
}

type SortKey = 'executed_at' | 'direction' | 'open_close' | 'symbol' | 'asset_class' | 'strike' | 'option_type' | 'expiry' | 'quantity' | 'multiplier' | 'price' | 'commission' | 'pnl' | 'parent_id' | 'origin';
interface SortConfig {
  key: SortKey;
  direction: 'asc' | 'desc';
}

interface SortableHeaderProps {
  label: string;
  sortKey: SortKey;
  align?: 'left' | 'right';
  sortConfig: SortConfig | null;
  onSort: (key: SortKey) => void;
}

function SortableHeader({ label, sortKey, align = 'left', sortConfig, onSort }: SortableHeaderProps) {
  return (
    <th
      className={`px-3 py-2 text-${align} text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground select-none`}
      onClick={() => onSort(sortKey)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
        {label}
        {sortConfig?.key === sortKey ? (
          sortConfig.direction === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
        ) : (
          <ArrowUpDown size={12} className="opacity-30" />
        )}
      </div>
    </th>
  );
}

export function ExecutionLegsTable({ tradeId, trade }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [showDeleted, setShowDeleted] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [moveExecutionId, setMoveExecutionId] = useState<string | null>(null);
  const [detachExecutionId, setDetachExecutionId] = useState<string | null>(null);
  const [splitExecution, setSplitExecution] = useState<LogicalExecution | null>(null);
  const [linkExecution, setLinkExecution] = useState<LogicalExecution | null>(null);

  const { activePortfolio } = useActivePortfolio();

  // Fetch with include_deleted=true when the toggle is on so we can show them
  const { data: executions, isLoading, isError, refetch } = useTradeExecutions(tradeId, activePortfolio?.id, showDeleted);
  const reassignExecution = useReassignExecution();
  const detachExecution = useDetachExecution();

  // Count only non-deleted for the header badge
  const activeCount = executions?.filter((ex: LogicalExecution) => !ex.deleted).length ?? 0;
  const deletedCount = executions?.filter((e: LogicalExecution) => e.deleted).length ?? 0;

  const isClosedBeforeSplit =
    trade.quantity !== null &&
    trade.chart_quantity !== null &&
    trade.quantity !== trade.chart_quantity;

  const totalCount = executions?.length ?? 0;
  const hasSplitExecutions = executions?.some((e: LogicalExecution) => e.origin === "split") ?? false;
  const hasOptionLeg = executions?.some((ex: LogicalExecution) => ex.option_type !== null) ?? false;

  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);

  const handleSort = (key: SortKey) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const timelineItems = useMemo(() => {
    if (!executions) return [];
    type TimelineItem =
      | { type: "execution"; data: LogicalExecution }
      | { type: "corporate_action"; data: NonNullable<Trade["corporate_action_impact"]>[number] };

    const items: TimelineItem[] = executions.map((ex: LogicalExecution) => ({
      type: "execution",
      data: ex,
    }));

    if (trade.corporate_action_impact && !isClosedBeforeSplit) {
      trade.corporate_action_impact.forEach((ca) => {
        items.push({ type: "corporate_action", data: ca });
      });
    }

    if (sortConfig !== null) {
      items.sort((a, b) => {
        if (a.type === "corporate_action" || b.type === "corporate_action") {
          const dateA = a.type === "execution" ? a.data.executed_at : a.data.date;
          const dateB = b.type === "execution" ? b.data.executed_at : b.data.date;
          return dateA.localeCompare(dateB);
        }

        let aVal: string | number = a.data[sortConfig.key] ?? '';
        let bVal: string | number = b.data[sortConfig.key] ?? '';

        if (['quantity', 'price', 'pnl', 'commission', 'multiplier', 'strike'].includes(sortConfig.key)) {
          aVal = parseFloat(String(aVal || '0'));
          bVal = parseFloat(String(bVal || '0'));
        } else if (['executed_at', 'expiry'].includes(sortConfig.key)) {
          aVal = aVal ? new Date(aVal).getTime() : 0;
          bVal = bVal ? new Date(bVal).getTime() : 0;
        } else {
          aVal = (aVal || '').toString().toLowerCase();
          bVal = (bVal || '').toString().toLowerCase();
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    } else {
      items.sort((a, b) => {
        const dateA = a.type === "execution" ? a.data.executed_at : a.data.date;
        const dateB = b.type === "execution" ? b.data.executed_at : b.data.date;
        return dateA.localeCompare(dateB);
      });
    }

    return items;
  }, [executions, trade.corporate_action_impact, sortConfig, isClosedBeforeSplit]);

  // Compute duplicate pairs for task 11.2
  const conflictLegIds = new Set<string>();
  if (trade.has_conflict && executions) {
    const imported = executions.filter((e: LogicalExecution) => e.origin === "imported" && !e.deleted);
    const manual = executions.filter((e: LogicalExecution) => e.origin === "manual" && !e.deleted && !e.source_id);
    for (const imp of imported) {
      for (const man of manual) {
        if (
          imp.symbol === man.symbol &&
          imp.direction === man.direction &&
          imp.quantity === man.quantity &&
          imp.price === man.price &&
          Math.floor(new Date(imp.executed_at).getTime() / 1000) === Math.floor(new Date(man.executed_at).getTime() / 1000)
        ) {
          conflictLegIds.add(imp.id);
          conflictLegIds.add(man.id);
        }
      }
    }
  }

  const handleMoveToTrade = (executionId: string) => {
    setMoveExecutionId(executionId);
  };

  const handleDetach = (executionId: string) => {
    setDetachExecutionId(executionId);
  };

  const confirmDetach = () => {
    if (!detachExecutionId || !activePortfolio) return;
    detachExecution.mutate(
      { executionId: detachExecutionId, sourceTradeId: tradeId, portfolioId: activePortfolio.id },
      {
        onSettled: () => setDetachExecutionId(null),
      }
    );
  };

  return (
    <div className="solid-card">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 lg:flex-nowrap lg:gap-0 px-4 py-3 border-b border-border">
        <div className="flex min-w-0 flex-wrap items-center gap-3 lg:flex-nowrap">
          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-expanded={!collapsed}
            className="hidden lg:flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            Execution Legs
            {activeCount > 0 && (
              <span className="text-xs font-normal text-muted-foreground">({activeCount})</span>
            )}
          </button>

          <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground lg:hidden">
            Execution Legs <span className="font-mono text-xs font-normal text-muted-foreground">({activeCount})</span>
          </h2>

          {trade.position_id && (
            <span
              className="inline-flex items-center rounded border border-border bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground"
              title={`Position group: ${trade.position_id}`}
            >
              Position {trade.position_id.slice(0, 8)}
            </span>
          )}

          {hasSplitExecutions && trade.position_id && (
            <span className="inline-flex items-center rounded border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-primary">
              Metadata inherited
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Mobile must offer the toggle before deleted executions are fetched. */}
            <button
              onClick={() => setShowDeleted(!showDeleted)}
              className={`min-h-10 lg:min-h-0 text-xs px-2 py-1 rounded border transition-colors ${deletedCount > 0 || showDeleted ? "" : "lg:hidden"} ${
                showDeleted
                  ? "bg-muted text-foreground border-border"
                  : "text-muted-foreground border-border hover:bg-[color-mix(in_srgb,var(--muted)_50%,transparent)]"
              }`}
            >
              {showDeleted ? `Hide deleted (${deletedCount})` : deletedCount > 0 ? `Show deleted (${deletedCount})` : "Show deleted"}
            </button>

          <button
            onClick={() => setAddModalOpen(true)}
            className="inline-flex min-h-10 lg:min-h-0 items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Plus size={13} />
            Add Execution
          </button>
        </div>
      </div>

      {/* Table body */}
        <div className={`overflow-x-auto ${collapsed ? "lg:hidden" : ""}`}>
          {isLoading && (
            <div className="flex items-center justify-center py-8 text-muted-foreground gap-2">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Loading executions…</span>
            </div>
          )}
          {isError && (
            <div className="px-4 py-6 flex flex-col items-center justify-center gap-3 border border-destructive/20 rounded-lg bg-destructive/5 m-4">
              <span className="text-sm text-destructive font-medium">Could not load executions. Check backend connectivity.</span>
              <button
                onClick={() => refetch()}
                className="px-3 py-1.5 text-xs font-medium rounded-md bg-muted text-foreground hover:bg-muted/80 transition-colors border border-border"
              >
                Retry
              </button>
            </div>
          )}
          {!isLoading && !isError && activeCount === 0 && !showDeleted && (
            <div className="px-4 py-6 text-sm text-muted-foreground text-center">
              No execution legs yet. Click &quot;+ Add Execution&quot; to add one.
            </div>
          )}
          {!isLoading && !isError && totalCount === 0 && showDeleted && (
            <div className="px-4 py-6 text-sm text-muted-foreground text-center">
              No execution legs found.
            </div>
          )}
          {!isLoading && !isError && totalCount > 0 && (
            <>
            <table className="hidden lg:table w-full text-sm">
              <thead>
                 <tr className="border-b border-border bg-[color-mix(in_srgb,var(--muted)_40%,transparent)]">
                   <SortableHeader label="Date" sortKey="executed_at" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Side" sortKey="direction" sortConfig={sortConfig} onSort={handleSort} />
                  {trade.is_combo && (
                    <>
                       <SortableHeader label="Open/Close" sortKey="open_close" sortConfig={sortConfig} onSort={handleSort} />
                       <SortableHeader label="Symbol" sortKey="symbol" sortConfig={sortConfig} onSort={handleSort} />
                       <SortableHeader label="Asset Class" sortKey="asset_class" sortConfig={sortConfig} onSort={handleSort} />
                    </>
                  )}
                  {hasOptionLeg && (
                    <>
                       <SortableHeader label="Strike" sortKey="strike" align="right" sortConfig={sortConfig} onSort={handleSort} />
                       <SortableHeader label="Type" sortKey="option_type" sortConfig={sortConfig} onSort={handleSort} />
                       <SortableHeader label="Expiry" sortKey="expiry" sortConfig={sortConfig} onSort={handleSort} />
                    </>
                  )}
                   <SortableHeader label="Qty" sortKey="quantity" align="right" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Mult." sortKey="multiplier" align="right" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Price" sortKey="price" align="right" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Commission" sortKey="commission" align="right" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="P&L" sortKey="pnl" align="right" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Lineage" sortKey="parent_id" sortConfig={sortConfig} onSort={handleSort} />
                   <SortableHeader label="Status" sortKey="origin" sortConfig={sortConfig} onSort={handleSort} />
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {timelineItems.map((item) =>
                  item.type === "corporate_action" ? (
                    <tr key={`ca-${item.data.id}`} className="bg-muted/30">
                      <td colSpan={10 + (trade.is_combo ? 3 : 0) + (hasOptionLeg ? 3 : 0)}>
                        <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
                          <Split className="w-4 h-4" />
                          <span>
                            Corporate Action: Split {formatSplitRatio(item.data.ratio)} on {item.data.date}
                            {item.data.old_conid &&
                            item.data.new_conid &&
                            item.data.old_conid !== item.data.new_conid
                              ? " (Symbol changed)"
                              : ""}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <ExecutionRow
                      key={item.data.id}
                      execution={item.data}
                      trade={trade}
                      tradeId={tradeId}
                      colSpan={10 + (trade.is_combo ? 3 : 0) + (hasOptionLeg ? 3 : 0)}
                      onMoveToTrade={handleMoveToTrade}
                      onDetach={handleDetach}
                      onSplit={setSplitExecution}
                      onLinkBroker={setLinkExecution}
                      hasOptionLeg={hasOptionLeg}
                      isConflict={conflictLegIds.has(item.data.id)}
                    />
                  )
                )}
              </tbody>
            </table>
            <div className="space-y-3 p-3 lg:hidden" data-testid="execution-leg-card-list">
              {timelineItems.map((item) => item.type === "corporate_action" ? (
                <div key={`ca-${item.data.id}`} className="flex items-center gap-2 border-y border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
                  <Split className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="min-w-0 break-words font-mono">
                    Split {formatSplitRatio(item.data.ratio)} on {item.data.date}
                    {item.data.old_conid && item.data.new_conid && item.data.old_conid !== item.data.new_conid ? " (Symbol changed)" : ""}
                  </span>
                </div>
              ) : (
                <ExecutionLegCard
                  key={item.data.id}
                  execution={item.data}
                  trade={trade}
                  tradeId={tradeId}
                  onMoveToTrade={handleMoveToTrade}
                  onDetach={handleDetach}
                  onSplit={setSplitExecution}
                  onLinkBroker={setLinkExecution}
                  hasOptionLeg={hasOptionLeg}
                  isConflict={conflictLegIds.has(item.data.id)}
                />
              ))}
            </div>
            </>
          )}
        </div>

      {addModalOpen && (
        <AddExecutionModal
          tradeId={tradeId}
          trade={trade}
          onClose={() => setAddModalOpen(false)}
        />
      )}

      {/* Trade picker for "Move to..." */}
      {moveExecutionId && (
        <TradePickerModal
          excludeIds={[tradeId]}
          singleSelect
          confirmLabel="Move Here"
          onConfirm={(picked) => {
            const targetId = picked[0]?.id;
            if (!targetId || !moveExecutionId || !activePortfolio) return;
            reassignExecution.mutate(
              { executionId: moveExecutionId, sourceTradeId: tradeId, target_trade_id: targetId, portfolioId: activePortfolio.id },
              { onSuccess: () => setMoveExecutionId(null) }
            );
          }}
          onClose={() => setMoveExecutionId(null)}
        />
      )}

      {detachExecutionId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div role="dialog" aria-modal="true" aria-label="Detach Execution" className="w-full max-w-sm solid-card p-5 shadow-2xl">
            <h3 className="text-sm font-semibold text-foreground">Detach Execution</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Detach this execution into a new trade? The execution will be removed from this trade.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDetachExecutionId(null)}
                className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDetach}
                disabled={detachExecution.isPending}
                className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {detachExecution.isPending ? "Detaching..." : "Detach"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Execution Modal (task 8.9) */}
      {splitExecution && (
        <SplitExecutionModal
          execution={splitExecution}
          tradeId={tradeId}
          onClose={() => setSplitExecution(null)}
        />
      )}

      {linkExecution && (
        <LinkBrokerTransactionModal
          execution={linkExecution}
          tradeId={tradeId}
          onClose={() => setLinkExecution(null)}
        />
      )}
    </div>
  );
}
