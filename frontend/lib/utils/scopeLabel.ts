/**
 * Shared helper for converting a comma-separated taxonomy/annotation scope
 * string into a human-readable label.
 *
 * Examples:
 *   scopeLabel("trades")           → "Trades"
 *   scopeLabel("checkins")         → "Check-ins"
 *   scopeLabel("trades,checkins")  → "Trades, Check-ins"
 *   scopeLabel("trades,checkins,playbook") → "Trades, Check-ins, Playbook"
 */
export function scopeLabel(scopeStr: string): string {
  if (!scopeStr) return "";
  return scopeStr
    .split(",")
    .map((s) => {
      const part = s.trim();
      if (part === "trades") return "Trades";
      if (part === "checkins") return "Check-ins";
      if (part === "playbook") return "Playbook";
      return part;
    })
    .join(", ");
}
