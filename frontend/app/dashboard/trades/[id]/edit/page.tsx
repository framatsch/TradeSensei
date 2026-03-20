/**
 * Edit trade page — loads a trade and mounts TradeForm in edit mode.
 */

"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useTrade } from "@/hooks/useTrade";
import { TradeForm } from "@/components/trades/TradeForm";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import type { Trade } from "@/lib/types";

export default function EditTradePage() {
  const params = useParams();
  const router = useRouter();
  const tradeId = typeof params.id === "string" ? params.id : "";

  const { data: trade, isLoading, isError, error } = useTrade(tradeId);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (isError || !trade) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-red-400 font-medium mb-2">
          {isError ? "Failed to load trade." : "Trade not found."}
        </p>
        {isError && (
          <p className="text-slate-500 text-sm mb-4">{error.message}</p>
        )}
        <Link
          href="/dashboard/trades"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
        >
          Back to Trades
        </Link>
      </div>
    );
  }

  function handleSuccess(updated: Trade) {
    router.push(`/dashboard/trades/${updated.id}`);
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link
          href={`/dashboard/trades/${tradeId}`}
          className="inline-flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:text-slate-100 transition-colors"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-4 h-4"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back to Trade
        </Link>
      </div>

      <PageHeader
        title={`Edit ${trade.symbol}`}
        subtitle="Update trade details"
      />

      <TradeForm
        trade={trade}
        onSuccess={handleSuccess}
        onCancel={() => router.push(`/dashboard/trades/${tradeId}`)}
      />
    </div>
  );
}
