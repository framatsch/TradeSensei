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
 * AddExecutionModal — modal form for adding a manual execution leg to a trade.
 */

"use client";

import { useState } from "react";
import type { AssetClass, Direction, LogicalExecutionCreate, Trade } from "@/lib/types";
import { useCreateExecution } from "@/hooks/useExecutions";
import { extractApiError } from "@/lib/apiErrors";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";

interface Props {
  tradeId: string;
  trade: Trade;
  onClose: () => void;
}

const ASSET_CLASSES: AssetClass[] = ["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"];

function toLocalDatetimeValue(isoString: string): string {
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOString(localDatetime: string): string {
  return new Date(localDatetime).toISOString();
}

export function AddExecutionModal({ tradeId, trade, onClose }: Props) {
  const { activePortfolioId } = useActivePortfolio();
  const [direction, setDirection] = useState<Direction>("LONG");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [executedAt, setExecutedAt] = useState(toLocalDatetimeValue(new Date().toISOString()));
  const [commission, setCommission] = useState("0");
  const [pnl, setPnl] = useState("");
  const [assetClass, setAssetClass] = useState<AssetClass>(trade.asset_class ?? "EQUITY");
  const [multiplier, setMultiplier] = useState(String(trade.multiplier ?? 1));
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createExecution = useCreateExecution();

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

    if (!activePortfolioId) return;

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

    if (trade.is_combo) {
      payload.asset_class = assetClass;
      const parsedMultiplier = parseInt(multiplier, 10);
      if (!isNaN(parsedMultiplier) && parsedMultiplier > 0) {
        payload.multiplier = parsedMultiplier;
      }
    }

    createExecution.mutate({ tradeId, portfolioId: activePortfolioId, data: payload }, {
      onSuccess: () => {
        onClose();
      },
      onError: (err) => {
        setErrorMsg(extractApiError(err, "Failed to add execution."));
      },
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl border border-border">
        <h2 className="mb-5 text-xl font-bold text-foreground">Add Execution</h2>

        {errorMsg && (
          <div className="mb-4 rounded-md bg-[color-mix(in_srgb,var(--destructive)_15%,transparent)] border border-destructive p-3 text-sm text-destructive">
            {errorMsg}
          </div>
        )}

        <form id="add-execution-form" onSubmit={handleSubmit} className="space-y-4">
          {/* BUY / SELL toggle */}
          <fieldset>
            <legend className={labelCls}>Side</legend>
            <div className="flex rounded-lg border border-border overflow-hidden bg-muted p-0.5 gap-0.5">
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
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {side.label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Quantity */}
          <div>
            <label htmlFor="exec-quantity" className={labelCls}>Quantity</label>
            <input
              id="exec-quantity"
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
            <label htmlFor="exec-price" className={labelCls}>Price</label>
            <input
              id="exec-price"
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
            <label htmlFor="exec-executed-at" className={labelCls}>Executed At</label>
            <input
              id="exec-executed-at"
              type="datetime-local"
              className={inputCls}
              value={executedAt}
              onChange={(e) => setExecutedAt(e.target.value)}
              required
            />
          </div>

          {/* Commission */}
          <div>
            <label htmlFor="exec-commission" className={labelCls}>Commission (Optional)</label>
            <input
              id="exec-commission"
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
            <label htmlFor="exec-pnl" className={labelCls}>P&amp;L (Optional — leave blank to auto-compute)</label>
            <input
              id="exec-pnl"
              type="number"
              step="any"
              className={inputCls}
              value={pnl}
              onChange={(e) => setPnl(e.target.value)}
              placeholder="0.00"
            />
          </div>

          {trade.is_combo && (
            <>
              <div>
                <label htmlFor="exec-asset-class" className={labelCls}>Asset Class</label>
                <select
                  id="exec-asset-class"
                  className={inputCls}
                  value={assetClass}
                  onChange={(e) => setAssetClass(e.target.value as AssetClass)}
                >
                  {ASSET_CLASSES.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="exec-multiplier" className={labelCls}>Multiplier</label>
                <input
                  id="exec-multiplier"
                  type="number"
                  min="1"
                  step="1"
                  className={inputCls}
                  value={multiplier}
                  onChange={(e) => setMultiplier(e.target.value)}
                />
              </div>
            </>
          )}

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
              disabled={createExecution.isPending || !activePortfolioId}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {createExecution.isPending ? "Adding…" : "Add Execution"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
