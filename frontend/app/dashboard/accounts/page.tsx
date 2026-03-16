/**
 * Accounts page — manage broker accounts.
 */

"use client";

import { useAccounts } from "@/hooks/useAccounts";
import { AccountList } from "@/components/accounts/AccountList";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";

export default function AccountsPage() {
  const { data: accounts, isLoading, isError, error, refetch } = useAccounts();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-red-400 font-medium mb-2">Failed to load accounts.</p>
        <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Accounts"
        subtitle="Manage your broker accounts"
      />
      <AccountList accounts={accounts ?? []} />
    </div>
  );
}
