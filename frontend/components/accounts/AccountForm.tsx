/**
 * AccountForm — create or edit a broker account with typed credentials and sync settings.
 */

"use client";

import { useState } from "react";
import { useCreateAccount, useUpdateAccount } from "@/hooks/useAccounts";
import { Spinner } from "@/components/ui/Spinner";
import type { Account, AccountType, FlexFromDatePreset } from "@/lib/types";
import type { AxiosError } from "axios";

interface Props {
  account?: Account;
  onSave: () => void;
  onCancel: () => void;
}

const INPUT_CLASS =
  "w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary";
const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";

const ACCOUNT_TYPE_OPTIONS: { value: AccountType; label: string }[] = [
  { value: "manual", label: "Manual" },
  { value: "schwab", label: "Charles Schwab" },
  { value: "ibkr", label: "Interactive Brokers (IBKR)" },
];

const CREDENTIAL_FIELDS: Record<Exclude<AccountType, "manual">, { key: string; label: string }[]> = {
  schwab: [
    { key: "SCHWAB_APP_KEY", label: "App Key" },
    { key: "SCHWAB_APP_SECRET", label: "App Secret" },
  ],
  ibkr: [
    { key: "IBKR_FLEX_TOKEN", label: "Flex Token" },
    { key: "IBKR_FLEX_QUERY_ID", label: "Flex Query ID" },
  ],
};

export function AccountForm({ account, onSave, onCancel }: Props) {
  const isEditing = account !== undefined;

  const [name, setName] = useState(account?.name ?? "");
  const [accountNumber, setAccountNumber] = useState(account?.account_number ?? "");
  const [type, setType] = useState<AccountType>(account?.type ?? "manual");
  const [currency, setCurrency] = useState(account?.currency ?? "USD");
  const [credentials, setCredentials] = useState<Record<string, string>>({});

  // Sync settings
  const [syncDays, setSyncDays] = useState<number>(account?.settings?.sync_days ?? 30);
  const [flexPreset, setFlexPreset] = useState<FlexFromDatePreset>(
    account?.settings?.flex_from_date_preset ?? "ytd"
  );

  const createMutation = useCreateAccount();
  const updateMutation = useUpdateAccount(account?.id ?? "");

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutError = isEditing ? updateMutation.error : createMutation.error;

  const errorMessage = (() => {
    if (!mutError) return null;
    const axiosErr = mutError as AxiosError<{ detail?: string }>;
    return axiosErr.response?.data?.detail ?? mutError.message;
  })();

  const handleCredentialChange = (key: string, value: string) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const filledCredentials = Object.fromEntries(
      Object.entries(credentials).filter(([, v]) => v.trim() !== "")
    );
    const properties = Object.keys(filledCredentials).length > 0 ? filledCredentials : null;

    const payload = {
      name: name.trim(),
      account_number: accountNumber.trim() || null,
      type,
      currency: currency.trim() || "USD",
      properties,
      settings: {
        sync_days: syncDays,
        flex_from_date_preset: flexPreset,
        flex_custom_from_date: null,
      },
    };

    if (isEditing) {
      updateMutation.mutate(payload, { onSuccess: onSave });
    } else {
      createMutation.mutate(payload, { onSuccess: onSave });
    }
  };

  const credentialFields = type !== "manual" ? CREDENTIAL_FIELDS[type] : null;

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-card rounded-xl border border-border p-5 space-y-4"
    >
      <h3 className="text-sm font-semibold text-foreground">
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

        {/* Account Number */}
        <div>
          <label htmlFor="acct-number" className={LABEL_CLASS}>
            Account Number
          </label>
          <input
            id="acct-number"
            type="text"
            value={accountNumber}
            onChange={(e) => setAccountNumber(e.target.value)}
            placeholder="U1234567"
            maxLength={50}
            className={INPUT_CLASS}
          />
        </div>

        {/* Account Type */}
        <div>
          <label htmlFor="acct-type" className={LABEL_CLASS}>
            Account Type <span className="text-red-400">*</span>
          </label>
          <select
            id="acct-type"
            value={type}
            onChange={(e) => {
              setType(e.target.value as AccountType);
              setCredentials({});
            }}
            className={INPUT_CLASS}
          >
            {ACCOUNT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
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
            maxLength={3}
            value={currency}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())}
            placeholder="USD"
            className={INPUT_CLASS}
          />
        </div>
      </div>

      {/* Broker Credentials — only for non-manual accounts */}
      {credentialFields && (
        <div className="border border-border rounded-lg p-4 space-y-3">
          <div>
            <p className="text-xs font-semibold text-muted-foreground">
              API Credentials
            </p>
            <p className="text-xs text-muted-foreground dark:text-slate-400 mt-0.5">
              {isEditing && account?.has_api_keys
                ? "Credentials are already stored. Enter new values to replace them."
                : "Credentials are encrypted before storage and never returned in plain text."}
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {credentialFields.map((field) => (
              <div key={field.key}>
                <label htmlFor={`cred-${field.key}`} className={LABEL_CLASS}>
                  {field.label}
                </label>
                <input
                  id={`cred-${field.key}`}
                  type="password"
                  autoComplete="off"
                  value={credentials[field.key] ?? ""}
                  onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                  placeholder={isEditing && account?.has_api_keys ? "Leave blank to keep existing" : ""}
                  className={INPUT_CLASS}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sync Settings — only for API-connected accounts */}
      {type !== "manual" && (
        <div className="border border-border rounded-lg p-4 space-y-3">
          <div>
            <p className="text-xs font-semibold text-muted-foreground">
              Default Sync Settings
            </p>
            <p className="text-xs text-muted-foreground dark:text-slate-400 mt-0.5">
              These defaults are pre-filled on the Import page for this account.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Sync days — used for Schwab and as IBKR fallback */}
            <div>
              <label htmlFor="sync-days" className={LABEL_CLASS}>
                Default look-back
              </label>
              <select
                id="sync-days"
                value={syncDays}
                onChange={(e) => setSyncDays(Number(e.target.value))}
                className={INPUT_CLASS}
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 180 days</option>
                <option value={365}>Last 1 year</option>
              </select>
            </div>

            {/* Flex date preset — only relevant for IBKR */}
            {type === "ibkr" && (
              <div>
                <label htmlFor="flex-preset" className={LABEL_CLASS}>
                  Flex date range preset
                </label>
                <select
                  id="flex-preset"
                  value={flexPreset}
                  onChange={(e) => setFlexPreset(e.target.value as FlexFromDatePreset)}
                  className={INPUT_CLASS}
                >
                  <option value="ytd">Year to date (Jan 1 – Today)</option>
                  <option value="custom">Custom start date</option>
                </select>
                <p className="text-xs text-slate-400 dark:text-muted-foreground mt-1">
                  IBKR Flex maximum: 1 year. Custom start date can be set per-import.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {errorMessage && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
          {errorMessage}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-md text-sm transition-colors"
        >
          {isPending && <Spinner size="sm" />}
          {isPending ? "Saving…" : isEditing ? "Save Changes" : "Create Account"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-secondary hover:bg-slate-200 dark:hover:bg-slate-600 text-muted-foreground rounded-md text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

