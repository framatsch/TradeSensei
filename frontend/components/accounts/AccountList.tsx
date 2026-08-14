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
 * AccountList — table of broker accounts with create/edit/delete actions.
 */

"use client";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { useDeleteAccount, useClearAccountTrades } from "@/hooks/useAccounts";
import { AccountForm } from "./AccountForm";
import { AccountDeleteModal } from "./AccountDeleteModal";
import { AccountClearTradesModal } from "./AccountClearTradesModal";
import type { Account, AccountType } from "@/lib/types";

// ── Type badge ─────────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<AccountType, { label: string; className: string }> = {
  manual: {
    label: "Manual",
    className:
      "bg-secondary text-muted-foreground border border-border",
  },
  schwab: {
    label: "Schwab",
    className:
      "bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] text-primary border border-[color-mix(in_srgb,var(--primary)_20%,transparent)]",
  },
  ibkr: {
    label: "IBKR",
    className:
      "bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] text-primary border border-[color-mix(in_srgb,var(--primary)_20%,transparent)]",
  },
};

function TypeBadge({ type, hasApiKeys }: { type: AccountType; hasApiKeys: boolean }) {
  const badge = TYPE_BADGE[type];
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}
      >
        {badge.label}
      </span>
      {hasApiKeys && (
        <span
          title="API credentials stored"
          className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-emerald-900/40 border border-emerald-700 text-emerald-400 text-xs leading-none"
        >
          🔑
        </span>
      )}
    </span>
  );
}

interface Props {
  accounts: Account[];
}

export function AccountList({ accounts }: Props) {
  const [showNewForm, setShowNewForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingAccount, setDeletingAccount] = useState<Account | null>(null);
  const { mutate: deleteAccount, isPending: isDeleting } = useDeleteAccount();
  const [clearingAccount, setClearingAccount] = useState<Account | null>(null);
  const { mutate: clearTrades, isPending: isClearing } = useClearAccountTrades();

  const handleDelete = (accountId: string) => {
    deleteAccount(accountId, {
      onSuccess: () => setDeletingAccount(null),
      onError: (err) => {
        console.error("Failed to delete account:", err);
        alert(`Failed to delete account: ${err.message}`);
      }
    });
  };

  const handleClearTrades = (accountId: string) => {
    clearTrades(accountId, {
      onSuccess: (result) => {
        setClearingAccount(null);
        toast.success(
          `Cleared ${result.trades_deleted} trades and ${result.executions_deleted} executions from ${clearingAccount?.name ?? "account"}.`,
        );
      },
      onError: (err) => {
        console.error("Failed to clear trades:", err);
        toast.error(`Failed to clear trades: ${err.message}`);
      },
    });
  };

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {accounts.length === 0
            ? "No accounts found."
            : `${accounts.length} account${accounts.length === 1 ? "" : "s"}`}
        </p>
        <button
          type="button"
          onClick={() => {
            setShowNewForm(true);
            setEditingId(null);
          }}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm transition-colors"
        >
          + New Account
        </button>
      </div>

      {/* New account form */}
      {showNewForm && (
        <AccountForm
          onSave={() => setShowNewForm(false)}
          onCancel={() => setShowNewForm(false)}
        />
      )}

      {/* Empty state */}
      {accounts.length === 0 && !showNewForm && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <p className="text-muted-foreground text-sm">
            No accounts found. Add your first account.
          </p>
        </div>
      )}

      {/* Accounts table */}
      {accounts.length > 0 && (
        <div className="solid-card">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-[color-mix(in_srgb,var(--muted)_40%,transparent)]">
                {["Name", "Account No.", "Type", "Currency", "Active", "Actions"].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <React.Fragment key={account.id}>
                  <tr
                    className="border-b border-border/50 hover:bg-secondary/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-foreground">
                      {account.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground font-mono">
                      {account.account_number ?? <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      <TypeBadge type={account.type} hasApiKeys={account.has_api_keys} />
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {account.currency}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          account.is_active
                            ? "bg-[color-mix(in_srgb,var(--success)_10%,transparent)] text-success border border-[color-mix(in_srgb,var(--success)_20%,transparent)]"
                            : "bg-secondary text-muted-foreground border border-border"
                        }`}
                      >
                        {account.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            setEditingId((prev) =>
                              prev === account.id ? null : account.id
                            )
                          }
                          className="px-3 py-1 bg-secondary hover:bg-muted text-muted-foreground rounded-md text-xs transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setClearingAccount(account)}
                          className="px-3 py-1 bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] hover:bg-[color-mix(in_srgb,var(--danger)_20%,transparent)] text-danger rounded-md text-xs transition-colors"
                        >
                          Clear Trades
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeletingAccount(account)}
                          className="px-3 py-1 bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] hover:bg-[color-mix(in_srgb,var(--danger)_20%,transparent)] text-danger rounded-md text-xs transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Inline edit form */}
                  {editingId === account.id && (
                    <tr>
                      <td colSpan={6} className="px-4 py-3 bg-[color-mix(in_srgb,var(--muted)_30%,transparent)]">
                        <AccountForm
                          account={account}
                          onSave={() => setEditingId(null)}
                          onCancel={() => setEditingId(null)}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deletingAccount && (
        <AccountDeleteModal
          account={deletingAccount}
          onClose={() => setDeletingAccount(null)}
          onDelete={handleDelete}
          isDeleting={isDeleting}
        />
      )}

      {clearingAccount && (
        <AccountClearTradesModal
          account={clearingAccount}
          onClose={() => setClearingAccount(null)}
          onClearTrades={handleClearTrades}
          isClearing={isClearing}
        />
      )}
    </div>
  );
}
