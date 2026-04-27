"use client";

import { useState } from "react";
import { usePortfolios } from "@/hooks/usePortfolios";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useAccounts } from "@/hooks/useAccounts";
import { PORTFOLIO_COLORS } from "@/lib/constants/portfolioColors";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Star, Edit2, Trash2, Plus, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "react-hot-toast";
import {
  createPortfolioApiV1PortfoliosPost,
  updatePortfolioApiV1PortfoliosPortfolioIdPatch,
  deletePortfolioApiV1PortfoliosPortfolioIdDelete,
  freshStartImportApiV1PortfoliosPortfolioIdImportsAccountIdFreshStartPost,
} from "@/lib/api/index";

const CURRENCY_ALLOWLIST = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD"];

export function PortfolioSettings() {
  const qc = useQueryClient();
  const { portfolios, isLoading, isError } = usePortfolios();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const updateSettings = useUpdateSettings();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [wipeModalOpen, setWipeModalOpen] = useState<string | null>(null);

  const defaultPortfolioId = settings?.default_portfolio_id;

  const createMutation = useMutation({
    mutationFn: (data: any) => createPortfolioApiV1PortfoliosPost({ body: data }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      setCreating(false);
      toast.success("Portfolio created");
    },
    onError: () => toast.error("Failed to create portfolio"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      updatePortfolioApiV1PortfoliosPortfolioIdPatch({ path: { portfolio_id: id }, body: data }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      setEditingId(null);
      toast.success("Portfolio updated");
    },
    onError: () => toast.error("Failed to update portfolio"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePortfolioApiV1PortfoliosPortfolioIdDelete({ path: { portfolio_id: id } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      setDeleteConfirmId(null);
      toast.success("Portfolio deleted");
    },
    onError: (error: any) => {
      if (error?.status === 409) {
        toast.error("Remove all accounts before deleting this portfolio");
      } else {
        toast.error("Failed to delete portfolio");
      }
      setDeleteConfirmId(null);
    },
  });

  if (isLoading || settingsLoading) {
    return <div className="space-y-4 animate-pulse">
      {[1, 2].map(i => <div key={i} className="h-24 bg-muted/30 rounded-lg"></div>)}
    </div>;
  }

  if (isError) {
    return <div className="p-4 bg-danger/10 text-danger rounded-md flex items-center gap-2">
      <AlertCircle className="h-5 w-5" />
      <span>Failed to load portfolios</span>
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium text-foreground">Portfolios</h2>
          <p className="text-sm text-muted-foreground">Manage your trading portfolios and their base currencies.</p>
        </div>
        {!creating && (
          <button
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" /> Create Portfolio
          </button>
        )}
      </div>

      <div className="space-y-4">
        {creating && (
          <PortfolioForm 
            onSubmit={(data) => createMutation.mutate(data)}
            onCancel={() => setCreating(false)}
          />
        )}

        {portfolios?.map((portfolio: any) => (
          <div key={portfolio.id} className="relative overflow-hidden bg-card border border-border rounded-lg p-5 flex flex-col gap-4 shadow-sm">
            {editingId === portfolio.id ? (
              <PortfolioForm 
                initialData={portfolio}
                onSubmit={(data) => updateMutation.mutate({ id: portfolio.id, data })}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <>
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-6 h-6 rounded-full shrink-0 shadow-inner" 
                      style={{ backgroundColor: portfolio.color_hex || PORTFOLIO_COLORS[0] }} 
                    />
                    <div>
                      <h3 className="font-semibold text-foreground">{portfolio.name}</h3>
                      <p className="text-sm text-muted-foreground uppercase">{portfolio.base_currency}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => updateSettings.mutate({ default_portfolio_id: portfolio.id })}
                      title="Set as default"
                      className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <Star className={`h-5 w-5 ${defaultPortfolioId === portfolio.id ? "fill-[#eab308] text-[#eab308]" : ""}`} />
                    </button>
                    <button
                      onClick={() => setEditingId(portfolio.id)}
                      className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(portfolio.id)}
                      className="p-1.5 text-danger/70 hover:text-danger rounded-md hover:bg-danger/10 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {deleteConfirmId === portfolio.id && (
                  <div className="mt-2 p-3 bg-danger/5 border border-danger/20 rounded-md flex flex-col gap-3">
                    <div className="flex items-center gap-2 text-danger">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span className="text-sm font-medium">Delete {portfolio.name}? This action cannot be undone.</span>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <button 
                        onClick={() => setDeleteConfirmId(null)}
                        className="px-3 py-1.5 text-sm rounded bg-background hover:bg-muted border border-border transition-colors font-medium text-foreground"
                      >
                        Cancel
                      </button>
                      <button 
                        onClick={() => deleteMutation.mutate(portfolio.id)}
                        className="px-3 py-1.5 text-sm text-white rounded bg-danger hover:bg-danger/90 transition-colors font-medium"
                      >
                        Confirm Delete
                      </button>
                    </div>
                  </div>
                )}
                
                <div className="pt-3 border-t border-border flex justify-end">
                   <button 
                     onClick={() => setWipeModalOpen(portfolio.id)}
                     className="text-xs text-danger/80 hover:text-danger hover:underline transition-colors"
                   >
                     Wipe Portfolio Data...
                   </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {wipeModalOpen && (
        <WipeDataModal 
          portfolio={portfolios?.find((p: any) => p.id === wipeModalOpen)}
          onClose={() => setWipeModalOpen(null)} 
        />
      )}
    </div>
  );
}

function PortfolioForm({ initialData, onSubmit, onCancel }: { initialData?: any, onSubmit: (data: any) => void, onCancel: () => void }) {
  const [name, setName] = useState(initialData?.name || "");
  const [currency, setCurrency] = useState(initialData?.base_currency || "USD");
  const [color, setColor] = useState(initialData?.color_hex || PORTFOLIO_COLORS[0]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      base_currency: currency,
      color_hex: color,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border border-border rounded-lg bg-card space-y-4 shadow-sm">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-foreground">Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 text-foreground"
            placeholder="e.g. Day Trading"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-foreground">Base Currency</label>
          <select
            value={currency}
            onChange={e => setCurrency(e.target.value)}
            disabled={initialData?.has_trades}
            title={initialData?.has_trades ? "Cannot change currency after trades exist" : ""}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 text-foreground"
          >
            {CURRENCY_ALLOWLIST.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Color</label>
        <div className="flex flex-wrap gap-2">
          {PORTFOLIO_COLORS.map(c => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              className={`w-6 h-6 rounded-full transition-all ${color === c ? "ring-2 ring-offset-2 ring-offset-background ring-primary scale-110" : "hover:scale-110 opacity-80"}`}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4 border-t border-border mt-4">
        <button type="button" onClick={onCancel} className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted transition-colors">
          Cancel
        </button>
        <button type="submit" disabled={!name.trim()} className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors">
          Save
        </button>
      </div>
    </form>
  );
}

function WipeDataModal({ portfolio, onClose }: { portfolio: any, onClose: () => void }) {
  const [confirmName, setConfirmName] = useState("");
  const [wiping, setWiping] = useState(false);
  const [progress, setProgress] = useState("");
  
  // Need to always call useAccounts to respect hook rules
  const { data: accounts } = useAccounts(portfolio?.id);

  if (!portfolio) return null;

  const handleWipe = async () => {
    if (!accounts || wiping) return;
    setWiping(true);
    let successCount = 0;
    
    try {
      for (const account of accounts) {
        setProgress(`Wiping account: ${account.name}...`);
        await freshStartImportApiV1PortfoliosPortfolioIdImportsAccountIdFreshStartPost({
          path: { portfolio_id: portfolio.id, account_id: account.id },
          body: {
            file: new Blob([]), acknowledged: true
          }
        });
        successCount++;
      }
      toast.success(`Wiped data from ${successCount} account(s)`);
      onClose();
    } catch (error) {
      toast.error("Failed to wipe data");
      setWiping(false);
      setProgress("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex gap-3 text-danger">
          <AlertCircle className="h-6 w-6 shrink-0" />
          <h3 className="text-lg font-semibold">Danger Zone</h3>
        </div>
        
        <div className="space-y-3">
          <p className="text-sm text-foreground">
            This will permanently delete all trades, executions, and screenshots for all accounts in <strong className="text-danger">{portfolio.name}</strong>.
          </p>
          <p className="text-sm text-muted-foreground italic">
            Note: It will not delete the accounts themselves.
          </p>
        </div>

        <div className="space-y-2 bg-muted/30 p-3 rounded border border-border">
          <label className="text-sm text-foreground font-medium flex gap-1">
            Type <span className="font-bold text-danger select-none">{portfolio.name}</span> to confirm:
          </label>
          <input 
            type="text" 
            value={confirmName}
            onChange={e => setConfirmName(e.target.value)}
            disabled={wiping}
            placeholder={portfolio.name}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger text-foreground"
          />
        </div>

        {progress && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted p-2 rounded">
            <RefreshCw className="h-3 w-3 animate-spin shrink-0" /> 
            <span className="truncate">{progress}</span>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button 
            onClick={onClose} 
            disabled={wiping}
            className="px-4 py-2 text-sm font-medium rounded-md bg-background border border-border text-foreground hover:bg-muted disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleWipe}
            disabled={wiping || confirmName !== portfolio.name}
            className="px-4 py-2 text-sm font-medium rounded-md bg-danger text-white hover:bg-danger/90 disabled:opacity-50 transition-colors"
          >
            {wiping ? "Wiping Data..." : "Wipe All Data"}
          </button>
        </div>
      </div>
    </div>
  );
}
