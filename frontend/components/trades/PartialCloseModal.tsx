import { useState } from "react";
import type { Trade } from "@/lib/types";
import { usePartialCloseTrade } from "@/hooks/useTrade";
import type { AxiosError } from "axios";

interface Props {
  trade: Trade;
  isOpen: boolean;
  onClose: () => void;
}

function toLocalDatetimeValue(isoString: string | null): string {
  if (!isoString) return "";
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOWithOffset(localDatetime: string): string | null {
  if (!localDatetime) return null;
  return new Date(localDatetime + ":00Z").toISOString();
}

export function PartialCloseModal({ trade, isOpen, onClose }: Props) {
  const currentQuantity = parseFloat(trade.quantity);

  const [quantity, setQuantity] = useState<string>("");
  const [exitPrice, setExitPrice] = useState<string>("");
  const [closedAt, setClosedAt] = useState<string>(toLocalDatetimeValue(new Date().toISOString()));
  const [exitCommission, setExitCommission] = useState<string>("0");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const partialClose = usePartialCloseTrade(trade.id);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setErrorMsg("Quantity must be greater than 0");
      return;
    }
    if (qty > currentQuantity) {
      setErrorMsg(`Quantity cannot exceed current open quantity (${currentQuantity})`);
      return;
    }

    const price = parseFloat(exitPrice);
    if (isNaN(price) || price <= 0) {
      setErrorMsg("Exit price must be greater than 0");
      return;
    }

    const closedAtIso = toISOWithOffset(closedAt);
    if (!closedAtIso) {
      setErrorMsg("Close date is required");
      return;
    }

    let commission = null;
    if (exitCommission.trim() !== "") {
      const comm = parseFloat(exitCommission);
      if (!isNaN(comm) && comm >= 0) {
        commission = comm;
      }
    }

    partialClose.mutate(
      {
        quantity: qty,
        exit_price: price,
        closed_at: closedAtIso,
        exit_commission: commission,
      },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (err) => {
          const axiosErr = err as AxiosError<{ detail?: string }>;
          setErrorMsg(axiosErr.response?.data?.detail ?? "Failed to partial close trade.");
        },
      }
    );
  };

  const inputCls = "w-full rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";
  const labelCls = "mb-1 block text-sm font-medium text-muted-foreground";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-card p-6 shadow-xl border border-border">
        <h2 className="mb-4 text-xl font-bold text-foreground">Partial Close</h2>
        
        {errorMsg && (
          <div className="mb-4 rounded-md bg-red-900/20 border border-red-800 p-3 text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelCls}>
              Quantity to Close (Max: {currentQuantity})
            </label>
            <input
              type="number"
              step="any"
              className={inputCls}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder={`e.g. ${currentQuantity / 2}`}
              required
            />
          </div>

          <div>
            <label className={labelCls}>Exit Price</label>
            <input
              type="number"
              step="any"
              className={inputCls}
              value={exitPrice}
              onChange={(e) => setExitPrice(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>

          <div>
            <label className={labelCls}>Closed At (UTC)</label>
            <input
              type="datetime-local"
              className={inputCls}
              value={closedAt}
              onChange={(e) => setClosedAt(e.target.value)}
              required
            />
          </div>

          <div>
            <label className={labelCls}>Exit Commission (Optional)</label>
            <input
              type="number"
              step="any"
              className={inputCls}
              value={exitCommission}
              onChange={(e) => setExitCommission(e.target.value)}
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
              disabled={partialClose.isPending}
              className="rounded-md bg-[#6063dd] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              {partialClose.isPending ? "Submitting..." : "Partial Close"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
