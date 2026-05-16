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
