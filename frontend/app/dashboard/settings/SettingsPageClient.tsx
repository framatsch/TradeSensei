/**
 * SettingsPageClient — client component for the Settings page.
 *
 * Renders the tab bar and switches between General, Accounts & Integrations,
 * Corporate Actions, and Features tabs.
 * Supports linking to a specific tab via ?tab=<id>.
 */

"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { CorporateActionsSettings } from "@/components/settings/CorporateActionsSettings";
import FeaturesSettings from "@/components/settings/FeaturesSettings";
import { GeneralSettings } from "@/components/settings/GeneralSettings";
import { ApiTokensSettings } from "@/components/settings/ApiTokensSettings";
import { CheckinSettings } from "@/components/settings/CheckinSettings";
import { PortfoliosBrokersHub } from "@/components/settings/PortfoliosBrokersHub";

type Tab =
  | "general"
  | "integrations"
  | "api-tokens"
  | "corporate-actions"
  | "features"
  | "portfolios-brokers"
  | "checkin";

const TABS: { id: Tab; label: string }[] = [
  { id: "general", label: "General" },
  { id: "portfolios-brokers", label: "Portfolios & Brokers" },
  { id: "api-tokens", label: "API & Tokens" },
  { id: "corporate-actions", label: "Corporate Actions" },
  { id: "features", label: "Features" },
  { id: "checkin", label: "Check-in" },
];

export function SettingsPageClient() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>("general");

  // Allow linking to a specific tab via ?tab=integrations, ?tab=features, etc.
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "api-tokens") setActiveTab("api-tokens");
    else if (tabParam === "corporate-actions") setActiveTab("corporate-actions");
    else if (tabParam === "features") setActiveTab("features");
    else if (tabParam === "portfolios" || tabParam === "integrations") setActiveTab("portfolios-brokers");
    else if (tabParam === "portfolios-brokers") setActiveTab("portfolios-brokers");
    else if (tabParam === "checkin") setActiveTab("checkin");
    else if (tabParam === "general") setActiveTab("general");
  }, [searchParams]);

  return (
    <div className="space-y-6 max-w-4xl bg-card border border-border p-6 rounded-xl">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Manage your preferences, accounts, and broker integrations.
        </p>
      </div>

      {/* Tab bar */}
      <div className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-secondary p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${
              activeTab === tab.id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="pt-2">
        {activeTab === "general" && <GeneralSettings />}
        {activeTab === "portfolios-brokers" && <PortfoliosBrokersHub />}
        {activeTab === "api-tokens" && <ApiTokensSettings />}
        {activeTab === "corporate-actions" && <CorporateActionsSettings />}
        {activeTab === "features" && <FeaturesSettings />}
        {activeTab === "checkin" && <CheckinSettings />}
      </div>
    </div>
  );
}
