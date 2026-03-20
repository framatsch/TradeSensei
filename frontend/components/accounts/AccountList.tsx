/**
 * AccountList — table of broker accounts with create/edit/delete actions.
 */

"use client";

import React, { useState } from "react";
import { useDeleteAccount } from "@/hooks/useAccounts";
import { AccountForm } from "./AccountForm";
import type { Account, AccountType } from "@/lib/types";

// ── Type badge ─────────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<AccountType, { label: string; className: string }> = {
  manual: {
    label: "Manual",
    className:
      "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-600",
  },
  schwab: {
    label: "Schwab",
    className:
      "bg-blue-900/30 text-blue-400 border border-blue-800",
  },
  ibkr: {
    label: "IBKR",
    className:
      "bg-indigo-900/30 text-indigo-400 border border-indigo-800",
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
  const { mutate: deleteAccount } = useDeleteAccount();

  const handleDelete = (account: Account) => {
    if (!window.confirm(`Delete account "${account.name}"? This cannot be undone.`)) return;
    deleteAccount(account.id);
  };

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600 dark:text-slate-400">
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
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
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
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 text-center">
          <p className="text-slate-500 text-sm">
            No accounts found. Add your first account.
          </p>
        </div>
      )}

      {/* Accounts table */}
      {accounts.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                {["Name", "Account No.", "Type", "Currency", "Active", "Actions"].map((col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-xs font-medium text-slate-600 dark:text-slate-400 uppercase tracking-wider"
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
                    className="border-b border-slate-200 dark:border-slate-700/50 hover:bg-slate-100 dark:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-slate-100">
                      {account.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400 font-mono">
                      {account.account_number ?? <span className="text-slate-400 dark:text-slate-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      <TypeBadge type={account.type} hasApiKeys={account.has_api_keys} />
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                      {account.currency}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          account.is_active
                            ? "bg-emerald-900/50 text-emerald-400 border border-emerald-800"
                            : "bg-slate-100 dark:bg-slate-700 text-slate-500 border border-slate-300 dark:border-slate-600"
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
                          className="px-3 py-1 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-md text-xs transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(account)}
                          className="px-3 py-1 bg-red-900/40 hover:bg-red-800/60 text-red-400 rounded-md text-xs transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Inline edit form */}
                  {editingId === account.id && (
                    <tr>
                      <td colSpan={6} className="px-4 py-3 bg-slate-50 dark:bg-slate-900/30">
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
    </div>
  );
}
