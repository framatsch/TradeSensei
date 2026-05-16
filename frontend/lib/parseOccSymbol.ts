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
 * OCC Option Symbol Parser
 *
 * Parses the 21-character OCC standard option symbol format used by IBKR:
 *
 *   CHTR  251003P00240000
 *   ├──── underlying (6 chars, right-padded with spaces)
 *         ├──── expiry YYMMDD (6 chars)
 *               ├── type: C/P (1 char)
 *                ├──── strike × 1000, 8 digits (e.g. 00240000 → $240.00)
 *
 * Non-option symbols are returned as-is with no parsed fields.
 */

export interface ParsedOccSymbol {
  /** The raw OCC symbol as stored in the DB */
  raw: string;
  /** True when the symbol matched the OCC format */
  isOption: boolean;
  /** Underlying ticker (e.g. "CHTR", "SPX") */
  underlying: string;
  /** Expiry date or null for non-options */
  expiry: Date | null;
  /** Expiry formatted as "Oct 3, 2025" or null */
  expiryFormatted: string | null;
  /** "Call" | "Put" | null */
  optionType: "Call" | "Put" | null;
  /** Strike price in USD or null */
  strike: number | null;
  /** Strike formatted as "$240.00" or null */
  strikeFormatted: string | null;
}

/**
 * OCC suffix length: YYMMDD(6) + C/P(1) + strike×1000(8) = 15 characters.
 * IBKR uses this suffix regardless of underlying length, so any symbol with
 * ≥ 16 characters and a valid suffix may be an option (e.g. 21-char standard
 * symbols use a 6-char padded underlying, but longer underlyings like
 * "COMBO_TEST  260320C00100000" work identically with a variable prefix length).
 */
const OCC_SUFFIX_LENGTH = 15; // YYMMDD + C/P + 8-digit strike
const OCC_MIN_LENGTH = 1 + OCC_SUFFIX_LENGTH; // at least 1-char underlying

/**
 * Parse an OCC-format option symbol.
 *
 * Supports both the standard 21-character OCC format (6-char padded underlying)
 * and IBKR's extended format where the underlying may be longer than 6 characters.
 *
 * @param symbol - The raw symbol string from the trade record.
 * @returns Parsed fields, or a minimal stub with `isOption: false` for equities/indices.
 */
export function parseOccSymbol(symbol: string): ParsedOccSymbol {
  const trimmed = symbol.trim();

  // Too short to contain a valid OCC suffix
  if (trimmed.length < OCC_MIN_LENGTH) {
    return {
      raw: symbol,
      isOption: false,
      underlying: trimmed,
      expiry: null,
      expiryFormatted: null,
      optionType: null,
      strike: null,
      strikeFormatted: null,
    };
  }

  // The suffix is always the last 15 characters; the underlying is everything before.
  const suffixStart = trimmed.length - OCC_SUFFIX_LENGTH;
  const underlyingRaw = trimmed.substring(0, suffixStart);
  const expiryRaw = trimmed.substring(suffixStart, suffixStart + 6);   // YYMMDD
  const typeChar = trimmed.substring(suffixStart + 6, suffixStart + 7); // C or P
  const strikeRaw = trimmed.substring(suffixStart + 7, suffixStart + 15); // 8 digits

  const underlying = underlyingRaw.trim();

  // Parse expiry: YYMMDD → full Date
  const yy = parseInt(expiryRaw.substring(0, 2), 10);
  const mm = parseInt(expiryRaw.substring(2, 4), 10) - 1; // 0-indexed month
  const dd = parseInt(expiryRaw.substring(4, 6), 10);
  const fullYear = yy >= 0 && yy <= 50 ? 2000 + yy : 1900 + yy;
  const expiry = new Date(Date.UTC(fullYear, mm, dd));

  const expiryFormatted = expiry.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });

  const optionType: "Call" | "Put" | null =
    typeChar === "C" ? "Call" : typeChar === "P" ? "Put" : null;

  const strikeInt = parseInt(strikeRaw, 10);
  const strike = isNaN(strikeInt) ? null : strikeInt / 1000;
  const strikeFormatted =
    strike !== null
      ? `$${strike.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}`
      : null;

  // Validate that it really looks like an OCC symbol:
  // expiry must be 6 digits, type must be C/P, strike must be numeric, underlying non-empty
  if (!underlying || !optionType || strike === null || !/^\d{6}$/.test(expiryRaw) || !/^\d{8}$/.test(strikeRaw)) {
    return {
      raw: symbol,
      isOption: false,
      underlying: trimmed,
      expiry: null,
      expiryFormatted: null,
      optionType: null,
      strike: null,
      strikeFormatted: null,
    };
  }

  return {
    raw: symbol,
    isOption: true,
    underlying,
    expiry,
    expiryFormatted,
    optionType,
    strike,
    strikeFormatted,
  };
}
