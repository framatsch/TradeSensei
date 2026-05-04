export type FeatureFlagKey =
  | "risk_analytics"
  | "cash_and_dividends"
  | "tax_report"
  | "reporting_hub";

export const FEATURE_FLAGS: { key: FeatureFlagKey; label: string; description: string; comingSoon?: boolean }[] = [
  {
    key: "risk_analytics",
    label: "Risk Analytics",
    description: "Unlocks the Risk Metrics tab in Analytics.",
  },
  {
    key: "cash_and_dividends",
    label: "Cash & Dividends",
    description: "Show Cash & Dividends page and summary widgets.",
  },
  {
    key: "tax_report",
    label: "Tax Report",
    description: "Show the Tax Report page and export.",
  },
  {
    key: "reporting_hub",
    label: "Reporting Hub",
    description: "Show Reporting Hub in the dashboard.",
  },
];

export const ALL_FEATURE_KEYS: FeatureFlagKey[] = FEATURE_FLAGS.map((f) => f.key);

