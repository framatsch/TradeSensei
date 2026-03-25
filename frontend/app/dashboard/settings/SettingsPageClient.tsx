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
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage your preferences, accounts, and broker integrations.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex p-1 bg-secondary/50 rounded-xl w-fit border border-border/50">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all duration-300 ${
              activeTab === tab.id
                ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/40 shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-white/5"
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
