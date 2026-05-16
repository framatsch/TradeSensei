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
 * Data validation utilities for analytics reports.
 *
 * These helpers check whether trade records have the required fields for
 * specific report types and return structured validation results for UI display.
 */

import type { Trade } from "@/lib/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TradeValidationResult {
  /** True when all required fields are present. */
  valid: boolean;
  /** Human-readable names of missing fields. */
  missingFields: string[];
}

export interface DataSufficiencyReport {
  /** Total number of trades checked. */
  totalTrades: number;
  /** Trades that pass all field checks. */
  validTrades: number;
  /** Trades with at least one missing field. */
  invalidTrades: number;
  /** Percentage of valid trades (0–100). */
  coveragePercent: number;
  /** Example missing field names (deduplicated). */
  missingFieldSummary: string[];
}

// ─── Per-trade validators ─────────────────────────────────────────────────────

/**
 * Check whether a trade has the data required for Risk/Reward Ratio analysis.
 * Both a stop-loss price and a take-profit price are needed.
 */
export function validateTradeForRRR(trade: Trade): TradeValidationResult {
  const missingFields: string[] = [];

  if (!trade.stop_loss || trade.stop_loss === "0") {
    missingFields.push("Stop-Loss Price");
  }
  if (!trade.take_profit || trade.take_profit === "0") {
    missingFields.push("Take-Profit Price");
  }

  return { valid: missingFields.length === 0, missingFields };
}

/**
 * Check whether a trade has the data required for R-Multiple calculation.
 * Requires a realized P&L and a stop-loss to compute initial risk.
 */
export function validateTradeForRMultiple(trade: Trade): TradeValidationResult {
  const missingFields: string[] = [];

  if (trade.pnl === null || trade.pnl === undefined) {
    missingFields.push("Realized P&L");
  }
  if (!trade.stop_loss || trade.stop_loss === "0") {
    missingFields.push("Stop-Loss Price");
  }

  return { valid: missingFields.length === 0, missingFields };
}

// ─── Aggregated report ────────────────────────────────────────────────────────

/**
 * Run a validator over a list of trades and return a sufficiency report.
 *
 * @param trades  - Array of trades to validate.
 * @param validator - Per-trade validation function.
 */
export function buildSufficiencyReport(
  trades: Trade[],
  validator: (trade: Trade) => TradeValidationResult
): DataSufficiencyReport {
  if (trades.length === 0) {
    return {
      totalTrades: 0,
      validTrades: 0,
      invalidTrades: 0,
      coveragePercent: 0,
      missingFieldSummary: [],
    };
  }

  let validTrades = 0;
  const allMissingFields = new Set<string>();

  for (const trade of trades) {
    const result = validator(trade);
    if (result.valid) {
      validTrades++;
    } else {
      result.missingFields.forEach((f) => allMissingFields.add(f));
    }
  }

  const invalidTrades = trades.length - validTrades;
  const coveragePercent =
    trades.length > 0 ? Math.round((validTrades / trades.length) * 100) : 0;

  return {
    totalTrades: trades.length,
    validTrades,
    invalidTrades,
    coveragePercent,
    missingFieldSummary: Array.from(allMissingFields),
  };
}

// ─── Computed R-Multiple ──────────────────────────────────────────────────────

/**
 * Compute the R-Multiple for a single closed trade.
 *
 * R-Multiple = realized PnL / |initial risk per share × quantity|
 *
 * Returns `null` when stop-loss or P&L data is missing.
 */
export function computeRMultiple(trade: Trade): number | null {
  if (!trade.pnl || !trade.stop_loss || !trade.entry_price || !trade.quantity) {
    return null;
  }

  const pnl = parseFloat(trade.pnl);
  const stopLoss = parseFloat(trade.stop_loss);
  const entryPrice = parseFloat(trade.entry_price);
  const quantity = parseFloat(trade.quantity);

  const riskPerShare = Math.abs(entryPrice - stopLoss);
  const initialRisk = riskPerShare * Math.abs(quantity);

  if (initialRisk === 0) return null;

  return pnl / initialRisk;
}
