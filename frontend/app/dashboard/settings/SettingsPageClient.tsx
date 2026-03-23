/**
 * SettingsPageClient — client component for the Settings page.
 *
 * Renders the tab bar and switches between General and Accounts & Integrations tabs.
 * Supports linking to a specific tab via ?tab=integrations.
 */

"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { GeneralSettings } from "@/components/settings/GeneralSettings";
import { AccountSettings } from "@/components/settings/AccountSettings";
import { CorporateActionsSettings } from "@/components/settings/CorporateActionsSettings";

type Tab = "general" | "integrations" | "corporate-actions";

const TABS: { id: Tab; label: string }[] = [
  { id: "general", label: "General" },
  { id: "integrations", label: "Accounts & Integrations" },
  { id: "corporate-actions", label: "Corporate Actions" },
];

export function SettingsPageClient() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>("general");

  // Allow linking to a specific tab via ?tab=integrations or ?tab=corporate-actions
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "integrations") {
      setActiveTab("integrations");
    } else if (tabParam === "corporate-actions") {
      setActiveTab("corporate-actions");
    }
  }, [searchParams]);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Settings</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Manage your preferences, accounts, and broker integrations.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="pt-2">
        {activeTab === "general" && <GeneralSettings />}
        {activeTab === "integrations" && <AccountSettings />}
        {activeTab === "corporate-actions" && <CorporateActionsSettings />}
      </div>
    </div>
  );
}
