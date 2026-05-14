"use client";

import { useState, useEffect } from "react";
import { usePortfolios } from "@/hooks/usePortfolios";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useAccounts } from "@/hooks/useAccounts";
import { THEME_COLORS } from "@/lib/constants/colors";
import { Star, Edit2, Plus, ChevronDown, ChevronRight, AlertCircle, RefreshCw } from "lucide-react";
import type { PortfolioRead as Portfolio } from "@/lib/api/types.gen";
import type { Account } from "@/lib/types";
import { PortfolioCreateModal } from "./modals/PortfolioCreateModal";
import { PortfolioEditModal } from "./modals/PortfolioEditModal";
import { BrokerAccountCreateModal } from "./modals/BrokerAccountCreateModal";
import { BrokerAccountEditModal } from "./modals/BrokerAccountEditModal";

const BROKER_TYPE_LABELS: Record<string, string> = {
  ibkr: "IBKR",
  schwab: "Schwab",
  manual: "Manual",
};

const BROKER_TYPE_BADGES: Record<string, string> = {
  ibkr: "bg-indigo-900/30 text-indigo-400 border border-indigo-800",
  schwab: "bg-blue-900/30 text-blue-400 border border-blue-800",
  manual: "bg-secondary text-muted-foreground border border-border",
};

interface AccountRowProps {
  account: Account;
  portfolio: Portfolio;
  onEdit: (account: Account) => void;
}

function AccountRow({ account, portfolio, onEdit }: AccountRowProps) {
  const statusBadge = !account.is_active
    ? { label: "Inactive", className: "bg-secondary text-muted-foreground border border-border" }
    : account.has_api_keys
      ? { label: "Connected", className: "bg-emerald-900/50 text-emerald-400 border border-emerald-800" }
      : { label: "Manual", className: "bg-amber-900/30 text-amber-400 border border-amber-800" };

  const brokerBadge = BROKER_TYPE_BADGES[account.type] || BROKER_TYPE_BADGES.manual;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-muted/20 rounded-md border border-border/50">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">{account.name}</span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${brokerBadge}`}>
          {BROKER_TYPE_LABELS[account.type] || "Manual"}
        </span>
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusBadge.className}`}>
          {statusBadge.label}
        </span>
      </div>
      <button
        onClick={() => onEdit(account)}
        className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
      >
        <Edit2 className="h-4 w-4" />
      </button>
    </div>
  );
}

interface PortfolioAccountsProps {
  portfolio: Portfolio;
  onAddAccount: () => void;
  onEditAccount: (account: Account) => void;
}

function PortfolioAccounts({ portfolio, onAddAccount, onEditAccount }: PortfolioAccountsProps) {
  const { data: accounts, isLoading, isError } = useAccounts(portfolio.id);

  if (isLoading) {
    return (
      <div className="ml-8 space-y-2 animate-pulse">
        <div className="h-10 bg-muted/30 rounded-md" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="ml-8 p-3 bg-danger/10 text-danger rounded-md flex items-center gap-2 text-sm">
        <AlertCircle className="h-4 w-4 shrink-0" />
        <span>Failed to load accounts</span>
      </div>
    );
  }

  const accountList = accounts ?? [];

  return (
    <div className="ml-8 space-y-2">
      {accountList.map((account: Account) => (
        <AccountRow
          key={account.id}
          account={account}
          portfolio={portfolio}
          onEdit={onEditAccount}
        />
      ))}
      {accountList.length === 0 && (
        <p className="text-xs text-muted-foreground py-2 text-center">No broker accounts linked</p>
      )}
      <button
        onClick={onAddAccount}
        className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 transition-colors font-medium"
      >
        <Plus className="h-3.5 w-3.5" /> Add Broker Account
      </button>
    </div>
  );
}

export function PortfoliosBrokersHub() {
  const { portfolios, isLoading, isError } = usePortfolios();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const updateSettings = useUpdateSettings();

  const [expandedPortfolioIds, setExpandedPortfolioIds] = useState<Set<string>>(new Set());
  const [initialized, setInitialized] = useState(false);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalPortfolio, setEditModalPortfolio] = useState<Portfolio | null>(null);
  const [addAccountPortfolio, setAddAccountPortfolio] = useState<Portfolio | null>(null);
  const [editAccount, setEditAccount] = useState<Account | null>(null);

  const defaultPortfolioId = settings?.default_portfolio_id;

  useEffect(() => {
    if (!initialized && portfolios && portfolios.length === 1) {
      setExpandedPortfolioIds(new Set([portfolios[0].id]));
      setInitialized(true);
    } else if (!initialized && portfolios && portfolios.length !== 1) {
      setInitialized(true);
    }
  }, [portfolios, initialized]);

  const toggleExpand = (id: string) => {
    setExpandedPortfolioIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSetDefault = (portfolioId: string) => {
    updateSettings.mutate({ default_portfolio_id: portfolioId });
  };

  if (isLoading || settingsLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2].map((i) => (
          <div key={i} className="h-24 bg-muted/30 rounded-lg" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 bg-danger/10 text-danger rounded-md flex items-center gap-2">
        <AlertCircle className="h-5 w-5" />
        <span>Failed to load portfolios</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium text-foreground">Portfolios &amp; Brokers</h2>
          <p className="text-sm text-muted-foreground">
            Manage your trading portfolios and their linked broker accounts.
          </p>
        </div>
        <button
          onClick={() => setCreateModalOpen(true)}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" /> Create New Portfolio
        </button>
      </div>

      {portfolios && portfolios.length === 0 ? (
        <div className="bg-card border border-border rounded-lg p-12 text-center">
          <p className="text-muted-foreground text-sm">No portfolios yet. Create your first portfolio to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {portfolios?.map((portfolio: Portfolio) => {
            const isExpanded = expandedPortfolioIds.has(portfolio.id);
            return (
              <div
                key={portfolio.id}
                className="bg-card border border-border rounded-lg overflow-hidden shadow-sm"
              >
                <div className="flex items-center justify-between px-5 py-4">
                  <button
                    onClick={() => toggleExpand(portfolio.id)}
                    className="flex items-center gap-3 flex-1 min-w-0 text-left"
                  >
                    <div
                      className="w-5 h-5 rounded-full shrink-0 shadow-inner"
                      style={{ backgroundColor: portfolio.color_hex || THEME_COLORS[0] }}
                    />
                    <div className="min-w-0">
                      <h3 className="font-semibold text-foreground truncate">{portfolio.name}</h3>
                      <p className="text-sm text-muted-foreground uppercase">{portfolio.base_currency}</p>
                    </div>
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
                    )}
                  </button>
                  <div className="flex items-center gap-1 ml-2">
                    <button
                      onClick={() => handleSetDefault(portfolio.id)}
                      title="Set as default"
                      aria-label="Set as default"
                      data-testid="set-default-portfolio"
                      className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <Star
                        className={`h-5 w-5 ${
                          defaultPortfolioId === portfolio.id ? "fill-[#eab308] text-[#eab308]" : ""
                        }`}
                      />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditModalPortfolio(portfolio);
                      }}
                      className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-4 pt-1">
                    <PortfolioAccounts
                      portfolio={portfolio}
                      onAddAccount={() => setAddAccountPortfolio(portfolio)}
                      onEditAccount={(account) => setEditAccount(account)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {createModalOpen && (
        <PortfolioCreateModal onClose={() => setCreateModalOpen(false)} />
      )}

      {editModalPortfolio && (
        <PortfolioEditModal
          portfolio={editModalPortfolio}
          onClose={() => setEditModalPortfolio(null)}
        />
      )}

      {addAccountPortfolio && (
        <BrokerAccountCreateModal
          portfolioId={addAccountPortfolio.id}
          portfolioName={addAccountPortfolio.name}
          onClose={() => setAddAccountPortfolio(null)}
        />
      )}

      {editAccount && (
        <BrokerAccountEditModal
          account={editAccount}
          onClose={() => setEditAccount(null)}
        />
      )}
    </div>
  );
}