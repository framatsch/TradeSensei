/**
 * New trade page — create a trade using the shared TradeForm.
 */

"use client";

import Link from "next/link";
import { TradeForm } from "@/components/trades/TradeForm";
import { PageHeader } from "@/components/ui/PageHeader";

export default function NewTradePage() {
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link
          href="/dashboard/trades"
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
          Back to Trades
        </Link>
      </div>

      <PageHeader title="New Trade" subtitle="Record a new trading position" />

      <TradeForm />
    </div>
  );
}
