/**
 * CashPageClient — client component for Cash & Dividends page.
 * Provides account selection, summary metrics, filtered transaction table,
 * and add/edit/delete modal for cash transactions.
 */

"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { useAccounts } from "@/hooks/useAccounts";
import {
  useCashTransactions,
  useAccountMetrics,
  useCreateCashTransaction,
  useUpdateCashTransaction,
  useDeleteCashTransaction,
} from "@/hooks/useCashTransactions";
import type {
  CashTransaction,
  CashTransactionCreate,
  CashTransactionType,
} from "@/lib/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const TRANSACTION_TYPES: CashTransactionType[] = [
  "DIVIDEND",
  "WITHHOLDING_TAX",
  "DEPOSIT",
  "WITHDRAWAL",
  "INTEREST",
  "FEE",
  "OTHER",
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatEur(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const n = parseFloat(value);
  if (isNaN(n)) return "—";
  return `€${n.toFixed(2)}`;
}

function formatAmount(amount: string, currency: string): string {
  const n = parseFloat(amount);
  if (isNaN(n)) return `${amount} ${currency}`;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)} ${currency}`;
}

function formatDate(dateStr: string): string {
  // ISO date strings: return just the YYYY-MM-DD part
  return dateStr.slice(0, 10);
}

// ─── Type badge ───────────────────────────────────────────────────────────────

interface TypeBadgeProps {
  type: CashTransactionType;
}

const TYPE_BADGE_CLASSES: Record<CashTransactionType, string> = {
  DIVIDEND:        "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  DEPOSIT:         "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  INTEREST:        "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  WITHHOLDING_TAX: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  FEE:             "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  WITHDRAWAL:      "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-primary",
  OTHER:           "bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300",
};

function TypeBadge({ type }: TypeBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_BADGE_CLASSES[type]}`}
    >
      {type.replace(/_/g, " ")}
    </span>
  );
}

// ─── Summary card ─────────────────────────────────────────────────────────────

interface SummaryCardProps {
  label: string;
  value: string;
  colorClass?: string;
}

function SummaryCard({ label, value, colorClass = "text-foreground" }: SummaryCardProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4 flex flex-col gap-1">
      <p className="text-xs font-medium text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
        {label}
      </p>
      <p className={`text-xl font-bold ${colorClass}`}>{value}</p>
    </div>
  );
}

// ─── Transaction form modal ───────────────────────────────────────────────────

interface FormState {
  date: string;
  type: CashTransactionType;
  symbol: string;
  amount: string;
  currency: string;
  amount_eur: string;
  description: string;
}

const DEFAULT_FORM: FormState = {
  date: new Date().toISOString().slice(0, 16),
  type: "DIVIDEND",
  symbol: "",
  amount: "",
  currency: "USD",
  amount_eur: "",
  description: "",
};

interface TransactionModalProps {
  accountId: string;
  editing: CashTransaction | null;
  onClose: () => void;
}

function TransactionModal({ accountId, editing, onClose }: TransactionModalProps) {
  const [form, setForm] = useState<FormState>(() => {
    if (editing) {
      return {
        date: editing.date.slice(0, 16),
        type: editing.type,
        symbol: editing.symbol ?? "",
        amount: editing.amount,
        currency: editing.currency,
        amount_eur: editing.amount_eur ?? "",
        description: editing.description ?? "",
      };
    }
    return DEFAULT_FORM;
  });

  const { mutate: create, isPending: isCreating } = useCreateCashTransaction();
  const { mutate: update, isPending: isUpdating } = useUpdateCashTransaction();
  const isPending = isCreating || isUpdating;

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const payload: CashTransactionCreate = {
      date: form.date,
      type: form.type,
      symbol: form.symbol.trim() || null,
      amount: form.amount,
      currency: form.currency,
      amount_eur: form.amount_eur.trim() || null,
      description: form.description.trim() || null,
    };

    if (editing) {
      update(
        { id: editing.id, account_id: accountId, data: payload },
        { onSuccess: onClose }
      );
    } else {
      create(
        { account_id: accountId, data: payload },
        { onSuccess: onClose }
      );
    }
  }

  const inputClass =
    "w-full px-3 py-2 rounded-md border border-border dark:border-border " +
    "bg-white dark:bg-background text-foreground text-sm " +
    "focus:outline-none focus:ring-2 focus:ring-primary";

  const labelClass = "block text-xs font-medium text-muted-foreground mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-lg shadow-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-base font-semibold text-foreground mb-5">
          {editing ? "Edit Transaction" : "Add Transaction"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date */}
          <div>
            <label htmlFor="ct-date" className={labelClass}>Date *</label>
            <input
              id="ct-date"
              type="datetime-local"
              name="date"
              required
              value={form.date}
              onChange={handleChange}
              className={inputClass}
            />
          </div>

          {/* Type */}
          <div>
            <label htmlFor="ct-type" className={labelClass}>Type *</label>
            <select
              id="ct-type"
              name="type"
              required
              value={form.type}
              onChange={handleChange}
              className={inputClass}
            >
              {TRANSACTION_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          {/* Symbol */}
          <div>
            <label htmlFor="ct-symbol" className={labelClass}>Symbol (optional)</label>
            <input
              id="ct-symbol"
              type="text"
              name="symbol"
              value={form.symbol}
              onChange={handleChange}
              placeholder="e.g. AAPL"
              className={inputClass}
            />
          </div>

          {/* Amount + Currency */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="ct-amount" className={labelClass}>Amount *</label>
              <input
                id="ct-amount"
                type="number"
                name="amount"
                required
                step="any"
                value={form.amount}
                onChange={handleChange}
                placeholder="0.00"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="ct-currency" className={labelClass}>Currency *</label>
              <input
                id="ct-currency"
                type="text"
                name="currency"
                required
                value={form.currency}
                onChange={handleChange}
                placeholder="USD"
                maxLength={10}
                className={inputClass}
              />
            </div>
          </div>

          {/* Amount EUR */}
          <div>
            <label htmlFor="ct-amount-eur" className={labelClass}>Amount EUR (optional)</label>
            <input
              id="ct-amount-eur"
              type="number"
              name="amount_eur"
              step="any"
              value={form.amount_eur}
              onChange={handleChange}
              placeholder="0.00"
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="ct-description" className={labelClass}>Description (optional)</label>
            <textarea
              id="ct-description"
              name="description"
              rows={2}
              value={form.description}
              onChange={handleChange}
              placeholder="Optional notes…"
              className={inputClass}
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="px-4 py-2 bg-secondary hover:bg-zinc-200 dark:hover:bg-zinc-600 text-muted-foreground rounded-md text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-md text-sm font-medium transition-colors"
            >
              {isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── CashPageClient ───────────────────────────────────────────────────────────

export function CashPageClient() {
  const { data: accounts, isLoading: accountsLoading } = useAccounts();

  const PAGE_SIZE = 20;

  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<CashTransactionType | "">("");
  const [offset, setOffset] = useState<number>(0);
  const [allItems, setAllItems] = useState<CashTransaction[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingTx, setEditingTx] = useState<CashTransaction | null>(null);

  // Auto-select first account when accounts load
  useEffect(() => {
    if (accounts && accounts.length === 1 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts, selectedAccountId]);

  // Reset pagination + items when account or filter changes
  useEffect(() => {
    setOffset(0);
    setAllItems([]);
  }, [selectedAccountId, typeFilter]);

  const {
    data: page,
    isLoading: txLoading,
    isFetching,
  } = useCashTransactions({
    account_id: selectedAccountId,
    offset,
    limit: PAGE_SIZE,
    type: typeFilter || null,
  });

  // Accumulate items for "load more" pagination
  useEffect(() => {
    if (page) {
      if (offset === 0) {
        // First page or filter/account changed — replace items
        setAllItems(page.items);
      } else {
        // Subsequent pages — append
        setAllItems((prev) => [...prev, ...page.items]);
      }
    }
  // We intentionally only want this to run when `page` changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const { data: metrics, isLoading: metricsLoading } = useAccountMetrics(selectedAccountId);
  const { mutate: deleteTx } = useDeleteCashTransaction();

  // Computed net flow
  const netFlow = metrics
    ? (parseFloat(metrics.total_dividends) + parseFloat(metrics.total_withholding_tax)).toFixed(2)
    : null;

  function handleAccountChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedAccountId(e.target.value);
  }

  function handleTypeFilterChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setTypeFilter(e.target.value as CashTransactionType | "");
  }

  function handleLoadMore() {
    if (page && allItems.length < page.total) {
      setOffset((prev) => prev + PAGE_SIZE);
    }
  }

  function handleEdit(tx: CashTransaction) {
    setEditingTx(tx);
    setShowModal(true);
  }

  function handleDelete(tx: CashTransaction) {
    if (!window.confirm(`Delete this ${tx.type.replace(/_/g, " ")} transaction? This cannot be undone.`)) {
      return;
    }
    deleteTx({ id: tx.id, account_id: tx.account_id });
  }

  function handleOpenAddModal() {
    setEditingTx(null);
    setShowModal(true);
  }

  function handleCloseModal() {
    setShowModal(false);
    setEditingTx(null);
  }

  const selectedAccount = accounts?.find((a) => a.id === selectedAccountId);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <PageHeader
        title="Cash & Dividends"
        subtitle="Non-trade cash flows: dividends, fees, taxes, deposits"
      />

      {/* Account selector */}
      <div className="flex items-center gap-3">
        <label
          htmlFor="account-select"
          className="text-sm font-medium text-muted-foreground shrink-0"
        >
          Account
        </label>
        {accountsLoading ? (
          <Spinner size="sm" />
        ) : (
          <select
            id="account-select"
            value={selectedAccountId}
            onChange={handleAccountChange}
            className="px-3 py-2 rounded-md border border-border dark:border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">— Select an account —</option>
            {(accounts ?? []).map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
                {account.account_number ? ` (${account.account_number})` : ""}
              </option>
            ))}
          </select>
        )}
        {selectedAccount && (
          <span className="text-xs text-muted-foreground dark:text-zinc-400">
            {selectedAccount.currency} · {selectedAccount.type.toUpperCase()}
          </span>
        )}
      </div>

      {/* No account selected placeholder */}
      {!selectedAccountId && (
        <div className="flex items-center justify-center h-48 bg-card border border-border rounded-xl">
          <p className="text-sm text-muted-foreground dark:text-zinc-400">
            Select an account to view transactions.
          </p>
        </div>
      )}

      {selectedAccountId && (
        <>
          {/* Summary widgets */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {metricsLoading ? (
              <div className="sm:col-span-3 flex justify-center py-6">
                <Spinner size="md" />
              </div>
            ) : metrics ? (
              <>
                <SummaryCard
                  label="Total Dividends"
                  value={formatEur(metrics.total_dividends)}
                  colorClass="text-green-600 dark:text-green-400"
                />
                <SummaryCard
                  label="Total Withholding Tax"
                  value={formatEur(metrics.total_withholding_tax)}
                  colorClass="text-red-600 dark:text-red-400"
                />
                <SummaryCard
                  label="Net Flow (Dividends + Tax)"
                  value={netFlow !== null ? `€${netFlow}` : "—"}
                  colorClass={
                    netFlow !== null && parseFloat(netFlow) >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }
                />
              </>
            ) : (
              <div className="sm:col-span-3 text-sm text-muted-foreground dark:text-zinc-400">
                Unable to load metrics.
              </div>
            )}
          </div>

          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label
                htmlFor="type-filter"
                className="text-sm font-medium text-muted-foreground"
              >
                Type
              </label>
              <select
                id="type-filter"
                value={typeFilter}
                onChange={handleTypeFilterChange}
                className="px-3 py-2 rounded-md border border-border dark:border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">All Types</option>
                {TRANSACTION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={handleOpenAddModal}
              className="ml-auto px-4 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-md transition-colors"
            >
              + Add Transaction
            </button>
          </div>

          {/* Data table */}
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            {txLoading && offset === 0 ? (
              <div className="flex items-center justify-center h-48">
                <Spinner size="md" />
              </div>
            ) : allItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 gap-2">
                <p className="text-sm text-muted-foreground dark:text-zinc-400">
                  No cash transactions found.
                </p>
                <button
                  type="button"
                  onClick={handleOpenAddModal}
                  className="text-sm text-primary hover:text-blue-700 dark:text-primary dark:hover:text-blue-300 underline"
                >
                  Add your first transaction
                </button>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Date
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Type
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Symbol
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Amount
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Currency
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Amount (EUR)
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Description
                        </th>
                        <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground dark:text-zinc-400 uppercase tracking-wide">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {allItems.map((tx) => (
                        <tr
                          key={tx.id}
                          className="border-b border-zinc-100 dark:border-border/60 hover:bg-zinc-50 dark:hover:bg-zinc-700/30 transition-colors"
                        >
                          <td className="px-4 py-3 text-foreground whitespace-nowrap">
                            {formatDate(tx.date)}
                          </td>
                          <td className="px-4 py-3">
                            <TypeBadge type={tx.type} />
                          </td>
                          <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                            {tx.symbol ?? "—"}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums text-foreground whitespace-nowrap">
                            {formatAmount(tx.amount, tx.currency)}
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">
                            {tx.currency}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums text-muted-foreground whitespace-nowrap">
                            {tx.amount_eur !== null ? formatEur(tx.amount_eur) : "—"}
                          </td>
                          <td
                            className="px-4 py-3 text-muted-foreground max-w-xs truncate"
                            title={tx.description ?? undefined}
                          >
                            {tx.description ?? "—"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center gap-2">
                              {/* Edit button */}
                              <button
                                type="button"
                                onClick={() => handleEdit(tx)}
                                aria-label="Edit transaction"
                                className="p-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-blue-50 dark:hover:bg-blue-900/30 dark:hover:text-primary transition-colors"
                              >
                                <svg
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2"
                                  className="w-4 h-4"
                                >
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                                </svg>
                              </button>

                              {/* Delete button */}
                              <button
                                type="button"
                                onClick={() => handleDelete(tx)}
                                aria-label="Delete transaction"
                                className="p-1.5 rounded-md text-muted-foreground hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 dark:hover:text-red-400 transition-colors"
                              >
                                <svg
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="2"
                                  className="w-4 h-4"
                                >
                                  <polyline points="3 6 5 6 21 6" />
                                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                                  <path d="M10 11v6" />
                                  <path d="M14 11v6" />
                                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination footer */}
                <div className="flex items-center justify-between px-4 py-3 border-t border-border text-sm text-muted-foreground dark:text-zinc-400">
                  <span>
                    Showing {allItems.length}
                    {page?.total !== null && page?.total !== undefined
                      ? ` of ${page.total}`
                      : ""}{" "}
                    transactions
                  </span>
                  {page && allItems.length < page.total && (
                    <button
                      type="button"
                      onClick={handleLoadMore}
                      disabled={isFetching}
                      className="px-3 py-1.5 bg-secondary hover:bg-zinc-200 dark:hover:bg-zinc-600 text-muted-foreground rounded-md text-xs font-medium transition-colors disabled:opacity-60"
                    >
                      {isFetching ? "Loading…" : "Load more"}
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </>
      )}

      {/* Add / Edit modal */}
      {showModal && selectedAccountId && (
        <TransactionModal
          accountId={selectedAccountId}
          editing={editingTx}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}
