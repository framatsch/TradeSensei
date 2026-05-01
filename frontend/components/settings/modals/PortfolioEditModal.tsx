"use client";

import { useState, useId } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import {
  updatePortfolioApiV1PortfoliosPortfolioIdPatch,
  deletePortfolioApiV1PortfoliosPortfolioIdDelete,
} from "@/lib/api/index";
import { extractApiError } from "@/lib/api/errors";
import { PORTFOLIO_COLORS } from "@/lib/constants/portfolioColors";
import { X, AlertTriangle, Trash2 } from "lucide-react";
import { toast } from "react-hot-toast";
import type { PortfolioRead as Portfolio } from "@/lib/api/types.gen";

interface Props {
  portfolio: Portfolio;
  onClose: () => void;
}

export function PortfolioEditModal({ portfolio, onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState(portfolio.name);
  const [color, setColor] = useState(portfolio.color_hex || PORTFOLIO_COLORS[0]);
  const [confirmName, setConfirmName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const uid = useId();

  const updateMutation = useMutation({
    mutationFn: async (data: { name: string; color_hex: string }) => {
      const res = await updatePortfolioApiV1PortfoliosPortfolioIdPatch({
        path: { portfolio_id: portfolio.id },
        body: data,
      });
      if (res.error) {
        throw new Error(extractApiError(res.error, "Failed to update portfolio"));
      }
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      toast.success("Portfolio updated");
      onClose();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await deletePortfolioApiV1PortfoliosPortfolioIdDelete({
        path: { portfolio_id: portfolio.id },
      });
      if (res.error) {
        throw new Error(extractApiError(res.error, "Failed to delete portfolio"));
      }
      return res;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      toast.success("Portfolio deleted");
      onClose();
    },
    onError: (err: Error) => {
      setDeleteError(err.message);
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    updateMutation.mutate({
      name: name.trim(),
      color_hex: color,
    });
  };

  const handleDelete = () => {
    if (confirmName.trim() !== portfolio.name) return;
    setDeleteError(null);
    deleteMutation.mutate();
  };

  const canDelete = confirmName.trim() === portfolio.name && !deleteMutation.isPending;
  const canSave = name.trim().length > 0 && !updateMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm overflow-y-auto">
      <div className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Edit Portfolio</h3>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
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
              data-testid="edit-portfolio-name-input"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">Base Currency</label>
            <div className="inline-flex items-center px-3 py-1.5 bg-muted/50 border border-border rounded-md">
              <span className="text-sm font-mono text-foreground uppercase" data-testid="readonly-currency">
                {portfolio.base_currency}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Base currency cannot be changed after creation</p>
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
            <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="edit-error">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={updateMutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSave}
              className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              data-testid="save-edit-portfolio"
            >
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>

        <div className="border-t border-border pt-5 space-y-4">
          <div className="flex items-center gap-2 text-danger">
            <AlertTriangle className="h-5 w-5" />
            <h4 className="text-sm font-semibold">Danger Zone</h4>
          </div>

          <div className="bg-danger/5 border border-danger/20 rounded-md p-4 space-y-3" data-testid="danger-zone">
            <p className="text-sm text-danger">
              This will permanently delete this portfolio, all linked broker accounts, and all historical trade data. This action cannot be undone.
            </p>

            <div className="space-y-1.5">
              <label className="text-sm text-foreground font-medium">
                Type <span className="font-bold text-danger select-none">{portfolio.name}</span> to confirm:
              </label>
              <input
                type="text"
                value={confirmName}
                onChange={(e) => setConfirmName(e.target.value)}
                disabled={deleteMutation.isPending}
                placeholder={portfolio.name}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger text-foreground"
                data-testid="delete-confirm-input"
              />
            </div>

            {deleteError && (
              <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="delete-error">
                {deleteError}
              </p>
            )}

            <button
              onClick={handleDelete}
              disabled={!canDelete}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-danger text-white rounded-md hover:bg-danger/90 disabled:opacity-50 transition-colors"
              data-testid="delete-portfolio-button"
            >
              <Trash2 className="h-4 w-4" />
              {deleteMutation.isPending ? "Deleting..." : "Delete Portfolio"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}