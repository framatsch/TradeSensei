/**
 * ExecutionLegsTable — collapsible table showing all execution legs for a trade.
 */

"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Plus, Loader2 } from "lucide-react";
import { useTradeExecutions, useReassignExecution, useDetachExecution } from "@/hooks/useExecutions";
import { ExecutionRow } from "./ExecutionRow";
import { AddExecutionModal } from "./AddExecutionModal";
import { TradePickerModal } from "./TradePickerModal";

interface Props {
  tradeId: string;
}

export function ExecutionLegsTable({ tradeId }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [moveExecutionId, setMoveExecutionId] = useState<string | null>(null);

  const { data: executions, isLoading, isError } = useTradeExecutions(tradeId);
  const reassignExecution = useReassignExecution();
  const detachExecution = useDetachExecution();

  const count = executions?.length ?? 0;

  const handleMoveToTrade = (executionId: string) => {
    setMoveExecutionId(executionId);
  };

  const handleDetach = (executionId: string) => {
    if (!window.confirm("Detach this execution into a new trade? The execution will be removed from this trade.")) return;
    detachExecution.mutate(
      { executionId, sourceTradeId: tradeId },
      {
        onSuccess: (newTrade) => {
          // Optionally show a toast or navigate — for now just refresh
          window.dispatchEvent(new CustomEvent("trade-detached", { detail: { newTradeId: newTrade.id } }));
        },
      }
    );
  };

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-primary transition-colors"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
          Execution Legs
          {count > 0 && (
            <span className="text-xs font-normal text-muted-foreground">({count})</span>
          )}
        </button>
        <button
          onClick={() => setAddModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-[#6063dd] text-white hover:opacity-90 transition-opacity"
        >
          <Plus size={13} />
          Add Execution
        </button>
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
            <div className="px-4 py-4 text-sm text-red-500">
              Failed to load executions.
            </div>
          )}
          {!isLoading && !isError && count === 0 && (
            <div className="px-4 py-6 text-sm text-muted-foreground text-center">
              No execution legs yet. Click &quot;+ Add Execution&quot; to add one.
            </div>
          )}
          {!isLoading && !isError && count > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Date</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Side</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Qty</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Price</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Commission</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">P&amp;L</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Status</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {executions?.map((ex) => (
                  <ExecutionRow
                    key={ex.id}
                    execution={ex}
                    tradeId={tradeId}
                    onMoveToTrade={handleMoveToTrade}
                    onDetach={handleDetach}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {addModalOpen && (
        <AddExecutionModal
          tradeId={tradeId}
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
            if (!targetId || !moveExecutionId) return;
            reassignExecution.mutate(
              { executionId: moveExecutionId, sourceTradeId: tradeId, target_trade_id: targetId },
              { onSuccess: () => setMoveExecutionId(null) }
            );
          }}
          onClose={() => setMoveExecutionId(null)}
        />
      )}
    </div>
  );
}

