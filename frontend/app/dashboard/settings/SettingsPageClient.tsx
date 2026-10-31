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
 * SettingsPageClient — client component for the Settings page.
 *
 * Renders the tab bar and switches between General, Accounts & Integrations,
 * Corporate Actions, and Features tabs.
 * Supports linking to a specific tab via ?tab=<id>.
 */

"use client";

import { useState } from "react";
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

function readTab(value: string | null): Tab | undefined {
  if (value === "portfolios" || value === "integrations") return "portfolios-brokers";
  return TABS.find((tab) => tab.id === value)?.id;
}

export function SettingsPageClient() {
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const [activeTab, setActiveTab] = useState<Tab>(() => readTab(searchParams.get("tab")) ?? "general");
  const [previousQuery, setPreviousQuery] = useState(query);

  // Allow linking to a specific tab via ?tab=integrations, ?tab=features, etc.
  if (previousQuery !== query) {
    setPreviousQuery(query);
    const tab = readTab(searchParams.get("tab"));
    if (tab) setActiveTab(tab);
  }

  return (
    <div className="w-full min-h-full p-6 md:p-12 flex justify-center items-start">
      <div className="space-y-6 w-full max-w-4xl solid-card p-6 md:p-8 shadow-sm">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your preferences, accounts, and broker integrations.
          </p>
        </div>

        {/* Tab bar */}
        <div className="inline-flex flex-wrap items-center gap-0.5 rounded-lg border border-border bg-secondary p-1">
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
    </div>
  );
}
