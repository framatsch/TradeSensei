"use client";

import { useState, useId } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { createPortfolioApiV1PortfoliosPost } from "@/lib/api/index";
import { extractApiError } from "@/lib/api/errors";
import { PORTFOLIO_COLORS } from "@/lib/constants/portfolioColors";
import { X, AlertTriangle } from "lucide-react";
import { toast } from "react-hot-toast";

const CURRENCY_ALLOWLIST = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD"];

interface Props {
  onClose: () => void;
}

export function PortfolioCreateModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [color, setColor] = useState(PORTFOLIO_COLORS[0]);
  const [error, setError] = useState<string | null>(null);
  const uid = useId();

  const createMutation = useMutation({
    mutationFn: async (data: { name: string; base_currency: "USD" | "EUR" | "GBP" | "CHF" | "JPY" | "AUD" | "CAD"; color_hex: string }) => {
      const res = await createPortfolioApiV1PortfoliosPost({ body: data as any });
      if (res.error) {
        throw new Error(extractApiError(res.error, "Failed to create portfolio"));
      }
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      toast.success("Portfolio created");
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    createMutation.mutate({
      name: name.trim(),
      base_currency: currency as any,
      color_hex: color,
    });
  };

  const canSubmit = name.trim().length > 0 && !createMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Create Portfolio</h3>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor={`${uid}-name`} className="text-sm font-medium text-foreground">
              Portfolio Name
            </label>
            <input
              id={`${uid}-name`}
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
              placeholder="e.g. Day Trading"
              data-testid="portfolio-name-input"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor={`${uid}-currency`} className="text-sm font-medium text-foreground">
              Base Currency
            </label>
            <select
              id={`${uid}-currency`}
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
              data-testid="currency-select"
            >
              {CURRENCY_ALLOWLIST.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-md p-3 flex gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-500" data-testid="currency-warning">
              The base currency cannot be changed after the portfolio is created. It serves as the foundation for all performance metrics.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Color</label>
            <div className="flex flex-wrap gap-2">
              {PORTFOLIO_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  data-testid="color-chip"
                  aria-label={`color ${c}`}
                  aria-pressed={color === c}
                  onClick={() => setColor(c)}
                  className={`w-6 h-6 rounded-full transition-all ${
                    color === c
                      ? "ring-2 ring-offset-2 ring-offset-background ring-primary scale-110"
                      : "hover:scale-110 opacity-80"
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="create-error">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={createMutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              data-testid="submit-create-portfolio"
            >
              {createMutation.isPending ? "Creating..." : "Create Portfolio"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}