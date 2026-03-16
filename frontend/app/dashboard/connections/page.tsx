/**
 * Connections page — manage broker integrations.
 *
 * Shows all supported broker integrations and their connection status.
 * Currently supports: Schwab (OAuth PKCE).
 */

"use client";

import { SchwabConnectionCard } from "@/components/broker/SchwabConnectionCard";

export default function ConnectionsPage() {
  return (
    <div className="max-w-2xl space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Broker Connections</h1>
        <p className="text-slate-400 text-sm mt-1">
          Connect your brokerage accounts to automatically import trades.
        </p>
      </div>

      {/* Broker cards */}
      <div className="space-y-4">
        <SchwabConnectionCard />
      </div>

      {/* Footer note */}
      <p className="text-slate-500 text-xs">
        OAuth tokens are encrypted at rest. Trade Journal never stores your brokerage password.
      </p>
    </div>
  );
}
