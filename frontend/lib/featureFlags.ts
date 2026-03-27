export type FeatureFlagKey =
  | "risk_analytics"
  | "cash_and_dividends"
  | "tax_report";

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
    label: "Cash Report",
    description: "Show the Cash Report page and export.",
  },
];

export const ALL_FEATURE_KEYS: FeatureFlagKey[] = FEATURE_FLAGS.map((f) => f.key);

