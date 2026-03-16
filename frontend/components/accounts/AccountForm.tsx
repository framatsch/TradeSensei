/**
 * AccountForm — create or edit a broker account.
 */

"use client";

import { useState } from "react";
import { useCreateAccount, useUpdateAccount } from "@/hooks/useAccounts";
import { Spinner } from "@/components/ui/Spinner";
import type { Account } from "@/lib/types";
import type { AxiosError } from "axios";

interface Props {
  account?: Account;
  onSave: () => void;
  onCancel: () => void;
}

const INPUT_CLASS =
  "w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
const LABEL_CLASS = "block text-xs font-medium text-slate-400 mb-1";

export function AccountForm({ account, onSave, onCancel }: Props) {
  const isEditing = account !== undefined;

  const [name, setName] = useState(account?.name ?? "");
  const [broker, setBroker] = useState(account?.broker ?? "");
  const [currency, setCurrency] = useState(account?.currency ?? "USD");
  const [description, setDescription] = useState(account?.description ?? "");

  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount(account?.id ?? "");

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutError = isEditing ? updateMutation.error : createMutation.error;

  const errorMessage = (() => {
    if (!mutError) return null;
    const axiosErr = mutError as AxiosError<{ detail?: string }>;
    return axiosErr.response?.data?.detail ?? mutError.message;
  })();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const payload = {
      name: name.trim(),
      broker: broker.trim() || null,
      currency: currency.trim() || "USD",
      description: description.trim() || null,
    };

    if (isEditing) {
      updateMutation.mutate(payload, { onSuccess: onSave });
    } else {
      createMutation.mutate(payload, { onSuccess: onSave });
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-slate-800 rounded-xl border border-slate-700 p-5 space-y-4"
    >
      <h3 className="text-sm font-semibold text-slate-200">
        {isEditing ? "Edit Account" : "New Account"}
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Name */}
        <div>
          <label htmlFor="acct-name" className={LABEL_CLASS}>
            Name <span className="text-red-400">*</span>
          </label>
          <input
            id="acct-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My IBKR Account"
            className={INPUT_CLASS}
          />
        </div>

        {/* Broker */}
        <div>
          <label htmlFor="acct-broker" className={LABEL_CLASS}>
            Broker
          </label>
          <input
            id="acct-broker"
            type="text"
            value={broker}
            onChange={(e) => setBroker(e.target.value)}
            placeholder="IBKR, Schwab…"
            className={INPUT_CLASS}
          />
        </div>

        {/* Currency */}
        <div>
          <label htmlFor="acct-currency" className={LABEL_CLASS}>
            Currency <span className="text-red-400">*</span>
          </label>
          <input
            id="acct-currency"
            type="text"
            required
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            placeholder="USD"
            className={INPUT_CLASS}
          />
        </div>
      </div>

      {/* Description */}
      <div>
        <label htmlFor="acct-desc" className={LABEL_CLASS}>
          Description
        </label>
        <textarea
          id="acct-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          placeholder="Optional notes about this account…"
          className={`${INPUT_CLASS} resize-none`}
        />
      </div>

      {errorMessage && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
          {errorMessage}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-md text-sm transition-colors"
        >
          {isPending && <Spinner size="sm" />}
          {isPending ? "Saving…" : isEditing ? "Save Changes" : "Create Account"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-md text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
