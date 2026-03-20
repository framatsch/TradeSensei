/**
 * Settings page — unified hub for user preferences, accounts, and broker integrations.
 *
 * Tabs:
 * - General: theme, default date range
 * - Accounts & Integrations: trading accounts + broker connections (Schwab, IBKR)
 */

import { Suspense } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { SettingsPageClient } from "./SettingsPageClient";

export const metadata = {
  title: "Settings — Trade Journal",
};

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      }
    >
      <SettingsPageClient />
    </Suspense>
  );
}
