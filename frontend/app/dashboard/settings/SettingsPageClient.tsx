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
import { AccountSettings } from "@/components/settings/AccountSettings";
import { CorporateActionsSettings } from "@/components/settings/CorporateActionsSettings";
import FeaturesSettings from "@/components/settings/FeaturesSettings";
import { PortfolioSettings } from "@/components/settings/PortfolioSettings";
import { ChartDisplaySettings } from "@/components/settings/ChartDisplaySettings";

type Tab = "look-and-feel" | "integrations" | "corporate-actions" | "features" | "portfolios";

const TABS: { id: Tab; label: string }[] = [
  { id: "look-and-feel", label: "Look & Feel" },
  { id: "integrations", label: "Accounts & Integrations" },
  { id: "corporate-actions", label: "Corporate Actions" },
  { id: "features", label: "Features" },
  { id: "portfolios", label: "Portfolios" },
];

export function SettingsPageClient() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>("look-and-feel");

  // Allow linking to a specific tab via ?tab=integrations, ?tab=features, etc.
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "integrations") {
      setActiveTab("integrations");
    } else if (tabParam === "corporate-actions") {
      setActiveTab("corporate-actions");
    } else if (tabParam === "features") {
      setActiveTab("features");
    } else if (tabParam === "portfolios") {
      setActiveTab("portfolios");
    } else if (tabParam === "look-and-feel") {
      setActiveTab("look-and-feel");
    }
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
        {activeTab === "look-and-feel" && <ChartDisplaySettings />}
        {activeTab === "integrations" && <AccountSettings />}
        {activeTab === "corporate-actions" && <CorporateActionsSettings />}
        {activeTab === "features" && <FeaturesSettings />}
        {activeTab === "portfolios" && <PortfolioSettings />}
      </div>
    </div>
  );
}
