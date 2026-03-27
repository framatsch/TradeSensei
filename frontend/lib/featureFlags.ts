export type FeatureFlagKey =
  | "rolling_winrate_chart"
  | "mae_mfe"
  | "cash_and_dividends"
  | "tax_report";

export const FEATURE_FLAGS: { key: FeatureFlagKey; label: string; description: string; comingSoon?: boolean }[] = [
  {
    key: "rolling_winrate_chart",
    label: "Rolling Win-Rate Chart",
    description: "Show rolling window win-rate chart on the Overview dashboard.",
  },
  {
    key: "mae_mfe",
    label: "MAE / MFE Metrics",
    description: "Mean adverse / favorable excursion metrics (coming soon).",
    comingSoon: true,
  },
  {
    key: "cash_and_dividends",
    label: "Cash & Dividends",
    description: "Show Cash & Dividends page and summary widgets.",
  },
  {
    key: "tax_report",
    label: "Steuerbericht",
    description: "Show the German tax report (Steuerbericht) page and export.",
  },
];

export const ALL_FEATURE_KEYS: FeatureFlagKey[] = FEATURE_FLAGS.map((f) => f.key);
