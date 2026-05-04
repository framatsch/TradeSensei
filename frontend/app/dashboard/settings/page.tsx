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
import { ContextSetter } from "@/components/layout/ContextSetter";

export const metadata = {
  title: "Settings — Trade Sensei",
};

export default function SettingsPage() {
  return (
    <>
      <ContextSetter context="none" />
      <Suspense
        fallback={
          <div className="flex items-center justify-center h-64">
            <Spinner size="lg" />
          </div>
        }
      >
        <SettingsPageClient />
      </Suspense>
    </>
  );
}
