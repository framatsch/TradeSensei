/**
 * @deprecated — replaced by global portfolio context
 * AccountFilter — dropdown to filter reports by broker account.
 * Shows "All Accounts" as the default option plus one entry per account.
 */
"use client";

import { useAccounts } from "@/hooks/useAccounts";

interface AccountFilterProps {
  value: string | null;
  onChange: (accountId: string | null) => void;
}

export function AccountFilter({ value, onChange }: AccountFilterProps) {
  const { data: accounts, isLoading } = useAccounts();

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
        Account
      </label>
      <div className="relative">
        <select
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={isLoading}
          className="appearance-none pl-3 pr-8 py-1.5 text-sm rounded-md border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 cursor-pointer min-w-[160px]"
        >
          <option value="">All Accounts</option>
          {(accounts ?? []).map((acc) => (
            <option key={acc.id} value={acc.id}>
              {acc.name}
              {acc.account_number ? ` (${acc.account_number})` : ""}
            </option>
          ))}
        </select>
        {/* chevron */}
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-3.5 h-3.5">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </div>
    </div>
  );
}
