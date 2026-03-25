/**
 * AccountSettings — account list for the Settings page.
 *
 * Broker credentials are now managed per-account within AccountForm.
 */

"use client";

import { useAccounts } from "@/hooks/useAccounts";
import { AccountList } from "@/components/accounts/AccountList";
import { Spinner } from "@/components/ui/Spinner";

export function AccountSettings() {
  const { data: accounts, isLoading, isError, error, refetch } = useAccounts();

  return (
    <div className="space-y-8">
      {/* ── Accounts ─────────────────────────────────────────────────── */}
      <div>
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-foreground">
            Trading Accounts
          </h3>
          <p className="text-xs text-muted-foreground dark:text-slate-400 mt-0.5">
            Manage your trading accounts. Set the account type and optionally store API credentials for automatic sync.
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Spinner size="md" />
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <p className="text-red-400 font-medium mb-2 text-sm">Failed to load accounts.</p>
            <p className="text-muted-foreground text-xs mb-3">{error?.message}</p>
            <button
              onClick={() => refetch()}
              className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-white rounded-md text-xs transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <AccountList accounts={accounts ?? []} />
        )}
      </div>
    </div>
  );
}
