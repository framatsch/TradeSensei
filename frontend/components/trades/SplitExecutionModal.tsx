/**
 * SplitExecutionModal — dialog to split one execution into two (task 8.9).
 *
 * Fields:
 *   - qty-A + qty-B (pre-filled 50/50, must sum to original qty)
 *   - price-A + price-B (pre-filled to original price)
 *   - executed_at-A + executed_at-B (pre-filled to original timestamp)
 *
 * Preview table shows both resulting rows before confirmation.
 * Confirm → POST /executions/{id}/split
 *
 * Design rules: no `dark:` modifier, semantic tokens only.
 */

"use client";

import { useState } from "react";
import { X } from "lucide-react";
import type { LogicalExecution } from "@/lib/types";
import { useSplitExecution } from "@/hooks/useExecutions";

interface Props {
  execution: LogicalExecution;
  tradeId: string;
  onClose: () => void;
}

function toDatetimeLocal(isoString: string): string {
  // Convert ISO string to datetime-local input value (YYYY-MM-DDTHH:mm)
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromDatetimeLocal(localStr: string): string {
  // Convert datetime-local value to ISO string with Z suffix
  if (!localStr) return "";
  return new Date(localStr).toISOString();
}

export function SplitExecutionModal({ execution, tradeId, onClose }: Props) {
  const originalQty = parseFloat(execution.quantity);
  const halfQty = (originalQty / 2).toFixed(4).replace(/\.?0+$/, "");
  const otherHalf = (originalQty - parseFloat(halfQty)).toFixed(4).replace(/\.?0+$/, "");

  const [qtyA, setQtyA] = useState(halfQty);
  const [qtyB, setQtyB] = useState(otherHalf);
  const [priceA, setPriceA] = useState(execution.price);
  const [priceB, setPriceB] = useState(execution.price);
  const [executedAtA, setExecutedAtA] = useState(toDatetimeLocal(execution.executed_at));
  const [executedAtB, setExecutedAtB] = useState(toDatetimeLocal(execution.executed_at));

  const splitMutation = useSplitExecution();

  const qtyANum = parseFloat(qtyA) || 0;
  const qtyBNum = parseFloat(qtyB) || 0;
  const qtySum = qtyANum + qtyBNum;
  const qtyValid = Math.abs(qtySum - originalQty) < 0.00001 && qtyANum > 0 && qtyBNum > 0;

  function handleConfirm() {
    if (!qtyValid) return;
    splitMutation.mutate(
      {
        executionId: execution.id,
        tradeId,
        data: {
          quantity_a: qtyA,
          quantity_b: qtyB,
          price_a: priceA || null,
          price_b: priceB || null,
          executed_at_a: executedAtA ? fromDatetimeLocal(executedAtA) : null,
          executed_at_b: executedAtB ? fromDatetimeLocal(executedAtB) : null,
        },
      },
      { onSuccess: () => onClose() }
    );
  }

  const fmt = (v: string) => {
    const n = parseFloat(v);
    return isNaN(n) ? "—" : `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
  };

  const fmtDt = (local: string) => {
    if (!local) return "—";
    return new Date(local).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-card shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Split Execution</h2>
          <button
            onClick={onClose}
            className="p-1 rounded text-muted-foreground hover:bg-muted transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Original summary */}
          <p className="text-xs text-muted-foreground">
            Splitting: <span className="font-mono text-foreground">{execution.direction}</span>{" "}
            <span className="font-mono text-foreground">{execution.quantity}</span> @ {fmt(execution.price)}
          </p>

          {/* Form grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Execution A */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-foreground">Execution A</p>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Quantity</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={qtyA}
                  onChange={(e) => setQtyA(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Price</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={priceA}
                  onChange={(e) => setPriceA(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Executed At</label>
                <input
                  type="datetime-local"
                  value={executedAtA}
                  onChange={(e) => setExecutedAtA(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
            </div>

            {/* Execution B */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-foreground">Execution B</p>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Quantity</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={qtyB}
                  onChange={(e) => setQtyB(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Price</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={priceB}
                  onChange={(e) => setPriceB(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Executed At</label>
                <input
                  type="datetime-local"
                  value={executedAtB}
                  onChange={(e) => setExecutedAtB(e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                />
              </div>
            </div>
          </div>

          {/* Validation warning */}
          {!qtyValid && (qtyA !== "" || qtyB !== "") && (
            <p className="text-xs text-red-500">
              Quantities must be positive and sum to {execution.quantity} (currently {qtySum.toFixed(4)}).
            </p>
          )}

          {/* Preview table */}
          {qtyValid && (
            <div className="border border-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40">
                    <th className="px-3 py-1.5 text-left font-medium text-muted-foreground">Leg</th>
                    <th className="px-3 py-1.5 text-right font-medium text-muted-foreground">Qty</th>
                    <th className="px-3 py-1.5 text-right font-medium text-muted-foreground">Price</th>
                    <th className="px-3 py-1.5 text-left font-medium text-muted-foreground">Executed At</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-border">
                    <td className="px-3 py-1.5 text-foreground font-medium">A</td>
                    <td className="px-3 py-1.5 text-right font-mono text-foreground">{qtyA}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-foreground">{fmt(priceA)}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{fmtDt(executedAtA)}</td>
                  </tr>
                  <tr>
                    <td className="px-3 py-1.5 text-foreground font-medium">B</td>
                    <td className="px-3 py-1.5 text-right font-mono text-foreground">{qtyB}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-foreground">{fmt(priceB)}</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{fmtDt(executedAtB)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!qtyValid || splitMutation.isPending}
            className="rounded-md bg-[#6063dd] px-4 py-1.5 text-sm text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {splitMutation.isPending ? "Splitting…" : "Confirm Split"}
          </button>
        </div>
      </div>
    </div>
  );
}
