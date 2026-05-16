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
 * New trade page — create a trade using the shared TradeForm.
 */

"use client";

import Link from "next/link";
import { TradeForm } from "@/components/trades/TradeForm";
import { PageHeader } from "@/components/ui/PageHeader";

export default function NewTradePage() {
  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/dashboard/trades"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
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
