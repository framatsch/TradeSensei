/**
 * AppConfig — central feature flag registry.
 *
 * Flags are controlled via NEXT_PUBLIC_* environment variables so they can
 * be toggled per deployment without code changes. Default is `false` (opt-in).
 *
 * Usage:
 *   import { AppConfig } from "@/lib/appConfig";
 *   if (AppConfig.enableTaxModule) { ... }
 */

export const AppConfig = {
  /**
   * Show the Cash Report (tax summary) in the navigation.
   * @default false
   */
  enableTaxModule: process.env.NEXT_PUBLIC_ENABLE_TAX_MODULE === "true",

  /**
   * Show the Cash & Dividends module in the navigation.
   * @default false
   */
  enableDividendModule: process.env.NEXT_PUBLIC_ENABLE_DIVIDEND_MODULE === "true",

  /**
   * Enable advanced efficiency metrics (MAE/MFE, efficiency score).
   * When false, placeholders with "data unavailable" are shown instead.
   * @default false
   */
  enableAdvancedEfficiency:
    process.env.NEXT_PUBLIC_ENABLE_ADVANCED_EFFICIENCY === "true",
} as const;

export type AppConfigKey = keyof typeof AppConfig;
