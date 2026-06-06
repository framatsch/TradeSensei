/**
 * Shared helper for converting a comma-separated taxonomy/annotation scope
 * string into a human-readable label.
 *
 * Examples:
 *   scopeLabel("trades")                      → "Trades"
 *   scopeLabel("checkins")                    → "Check-ins"
 *   scopeLabel("checkins,trades")             → "Check-ins, Trades"
 *   scopeLabel("checkins,playbook,trades")    → "Check-ins, Playbook, Trades"
 *   scopeLabel("both")                        → "Trades & Check-ins" (legacy compat)
 */
export function scopeLabel(scopeStr: string): string {
  if (!scopeStr) return "";
  // Legacy backwards-compat: "both" was the old enum value meaning trades + checkins.
  if (scopeStr === "both") return "Trades & Check-ins";
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
