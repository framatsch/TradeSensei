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
import { ChevronDown, ChevronRight, Plus, Loader2, Split } from "lucide-react";
import { useTradeExecutions, useReassignExecution, useDetachExecution } from "@/hooks/useExecutions";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { formatSplitRatio } from "@/lib/formatSplitRatio";
import { ExecutionRow } from "./ExecutionRow";
import { AddExecutionModal } from "./AddExecutionModal";
import { TradePickerModal } from "./TradePickerModal";
import { SplitExecutionModal } from "./SplitExecutionModal";
import { LinkBrokerTransactionModal } from "./LinkBrokerTransactionModal";
import type { LogicalExecution, Trade } from "@/lib/types";

interface Props {
  tradeId: string;
  trade: Trade;
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

    items.sort((a, b) => {
      const dateA = a.type === "execution" ? a.data.executed_at : a.data.date;
      const dateB = b.type === "execution" ? b.data.executed_at : b.data.date;
      return dateA.localeCompare(dateB);
    });

    return items;
  }, [executions, trade.corporate_action_impact]);

  const totalCount = executions?.length ?? 0;
  const hasSplitExecutions = executions?.some((e: LogicalExecution) => e.origin === "split") ?? false;
  const hasOptionLeg = executions?.some((ex: LogicalExecution) => ex.option_type !== null) ?? false;

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
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            Execution Legs
            {activeCount > 0 && (
              <span className="text-xs font-normal text-muted-foreground">({activeCount})</span>
            )}
          </button>

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

        <div className="flex items-center gap-2">
          {/* Show deleted toggle — only visible when there are deleted executions */}
          {(deletedCount > 0 || showDeleted) && (
            <button
              onClick={() => setShowDeleted(!showDeleted)}
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                showDeleted
                  ? "bg-muted text-foreground border-border"
                  : "text-muted-foreground border-border hover:bg-[color-mix(in_srgb,var(--muted)_50%,transparent)]"
              }`}
            >
              {showDeleted ? `Hide deleted (${deletedCount})` : `Show deleted (${deletedCount})`}
            </button>
          )}

          <button
            onClick={() => setAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-opacity"
          >
            <Plus size={13} />
            Add Execution
          </button>
        </div>
      </div>

      {/* Table body */}
      {!collapsed && (
        <div className="overflow-x-auto">
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
            <table className="w-full text-sm">
              <thead>
                 <tr className="border-b border-border bg-[color-mix(in_srgb,var(--muted)_40%,transparent)]">
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Date</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Side</th>
                  {trade.is_combo && (
                    <>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Open/Close</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Symbol</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Asset Class</th>
                    </>
                  )}
                  {hasOptionLeg && (
                    <>
                      <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Strike</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Type</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Expiry</th>
                    </>
                  )}
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Qty</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Mult.</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Price</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Commission</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">P&amp;L</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Lineage</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Status</th>
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
          )}
        </div>
      )}

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
          <div className="w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-xl">
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
