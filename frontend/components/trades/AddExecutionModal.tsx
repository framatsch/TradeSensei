/**
 * AddExecutionModal — modal form for adding a manual execution leg to a trade.
 */

"use client";

import { useState } from "react";
import type { Direction, LogicalExecutionCreate } from "@/lib/types";
import { useCreateExecution } from "@/hooks/useExecutions";
import type { AxiosError } from "axios";

interface Props {
  tradeId: string;
  onClose: () => void;
}

function toLocalDatetimeValue(isoString: string): string {
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOString(localDatetime: string): string {
  return new Date(localDatetime).toISOString();
}

export function AddExecutionModal({ tradeId, onClose }: Props) {
  const [direction, setDirection] = useState<Direction>("LONG");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [executedAt, setExecutedAt] = useState(toLocalDatetimeValue(new Date().toISOString()));
  const [commission, setCommission] = useState("0");
  const [pnl, setPnl] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createExecution = useCreateExecution(tradeId);

  const inputCls =
    "w-full rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";
  const labelCls = "mb-1 block text-sm font-medium text-muted-foreground";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setErrorMsg("Quantity must be greater than 0.");
      return;
    }

    const priceNum = parseFloat(price);
    if (isNaN(priceNum) || priceNum <= 0) {
      setErrorMsg("Price must be greater than 0.");
      return;
    }

    if (!executedAt) {
      setErrorMsg("Executed At date is required.");
      return;
    }

    const payload: LogicalExecutionCreate = {
      direction,
      quantity: qty.toString(),
      price: priceNum.toString(),
      executed_at: toISOString(executedAt),
    };

    const commNum = parseFloat(commission);
    if (!isNaN(commNum) && commNum >= 0) {
      payload.commission = commNum.toString();
    }

    const pnlNum = parseFloat(pnl);
    if (pnl.trim() !== "" && !isNaN(pnlNum)) {
      payload.pnl = pnlNum.toString();
    }

    createExecution.mutate(payload, {
      onSuccess: () => {
        onClose();
      },
      onError: (err) => {
        const axiosErr = err as AxiosError<{ detail?: string }>;
        setErrorMsg(axiosErr.response?.data?.detail ?? "Failed to add execution.");
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl border border-border">
        <h2 className="mb-5 text-xl font-bold text-foreground">Add Execution</h2>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-900/20 border border-red-800 p-3 text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        <form id="add-execution-form" onSubmit={handleSubmit} className="space-y-4">
          {/* BUY / SELL toggle */}
          <div>
            <label className={labelCls}>Side</label>
            <div className="flex rounded-lg border border-border overflow-hidden bg-[#e9e9e9] dark:bg-secondary p-0.5 gap-0.5">
              {[
                { label: "BUY", value: "LONG" as Direction },
                { label: "SELL", value: "SHORT" as Direction },
              ].map((side) => (
                <button
                  key={side.value}
                  type="button"
                  onClick={() => setDirection(side.value)}
                  className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
                    direction === side.value
                      ? "bg-[#6063dd] text-white"
                      : "text-[#717174] hover:text-foreground"
                  }`}
                >
                  {side.label}
                </button>
              ))}
            </div>
          </div>

          {/* Quantity */}
          <div>
            <label className={labelCls}>Quantity</label>
            <input
              type="number"
              step="any"
              min="0"
              className={inputCls}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="e.g. 100"
              required
            />
          </div>

          {/* Price */}
          <div>
            <label className={labelCls}>Price</label>
            <input
              type="number"
              step="any"
              min="0"
              className={inputCls}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>

          {/* Executed At */}
          <div>
            <label className={labelCls}>Executed At</label>
            <input
              type="datetime-local"
              className={inputCls}
              value={executedAt}
              onChange={(e) => setExecutedAt(e.target.value)}
              required
            />
          </div>

          {/* Commission */}
          <div>
            <label className={labelCls}>Commission (Optional)</label>
            <input
              type="number"
              step="any"
              min="0"
              className={inputCls}
              value={commission}
              onChange={(e) => setCommission(e.target.value)}
              placeholder="0.00"
            />
          </div>

          {/* P&L */}
          <div>
            <label className={labelCls}>P&amp;L (Optional — leave blank to auto-compute)</label>
            <input
              type="number"
              step="any"
              className={inputCls}
              value={pnl}
              onChange={(e) => setPnl(e.target.value)}
              placeholder="0.00"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createExecution.isPending}
              className="rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              {createExecution.isPending ? "Adding…" : "Add Execution"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
