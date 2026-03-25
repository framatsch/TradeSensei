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

/** OCC symbol length is exactly 21 characters (6 + 6 + 1 + 8) */
const OCC_LENGTH = 21;

/**
 * Parse an OCC-format option symbol.
 *
 * @param symbol - The raw symbol string from the trade record.
 * @returns Parsed fields, or a minimal stub with `isOption: false` for equities/indices.
 */
export function parseOccSymbol(symbol: string): ParsedOccSymbol {
  const trimmed = symbol.trim();

  // OCC symbols are exactly 21 chars; shorter ones are plain equity/index tickers
  if (trimmed.length !== OCC_LENGTH) {
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

  // Field positions according to OCC standard
  const underlyingRaw = trimmed.substring(0, 6);
  const expiryRaw = trimmed.substring(6, 12);   // YYMMDD
  const typeChar = trimmed.substring(12, 13);    // C or P
  const strikeRaw = trimmed.substring(13, 21);   // 8-digit integer, strike × 1000

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

  // Validate that it really looks like an OCC symbol
  if (!underlying || !optionType || strike === null) {
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
