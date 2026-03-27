/**
 * tradeFilterUtils.ts — shared utilities for trade filter ↔ URL conversion.
 *
 * Extracted from TradesPageClient so the sidebar (layout.tsx) can build
 * navigation URLs for saved views without duplicating the mapping logic.
 */

import type { TradeFilters } from "@/hooks/useTrades";

/**
 * Converts a saved-view definition (Record<string, any>) to URLSearchParams.
 * Used by the sidebar when navigating to a saved view.
 */
export function definitionToSearchParams(
  definition: Record<string, unknown>
): URLSearchParams {
  const p = new URLSearchParams();
  const d = definition as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

  if (d.symbol) p.set("symbol", String(d.symbol));
  if (d.direction) p.set("direction", String(d.direction));
  if (Array.isArray(d.asset_classes) && d.asset_classes.length)
    p.set("asset_class", (d.asset_classes as string[]).join(","));
  if (d.opened_at_from) p.set("opened_at_from", String(d.opened_at_from));
  if (d.opened_at_to) p.set("opened_at_to", String(d.opened_at_to));
  if (d.closed_at_from) p.set("closed_at_from", String(d.closed_at_from));
  if (d.closed_at_to) p.set("closed_at_to", String(d.closed_at_to));
  if (Array.isArray(d.tag_ids) && d.tag_ids.length)
    p.set("tag_ids", (d.tag_ids as string[]).join(","));
  if (d.playbook_id) p.set("playbook_id", String(d.playbook_id));
  if (d.pnl_positive !== null && d.pnl_positive !== undefined)
    p.set("pnl_positive", String(d.pnl_positive));
  if (d.status) p.set("status", String(d.status));
  if (d.account_id) p.set("account_id", String(d.account_id));
  if (d.hour_of_day !== undefined && d.hour_of_day !== null)
    p.set("hour_of_day", String(d.hour_of_day));
  if (d.day_of_week !== undefined && d.day_of_week !== null)
    p.set("day_of_week", String(d.day_of_week));

  return p;
}

/**
 * Serialises a TradeFilters object into a clean definition object suitable
 * for storing as a saved view (strips empty/null/undefined values).
 */
export function buildDefinitionFromFilters(
  filters: TradeFilters
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => {
      if (Array.isArray(value)) return value.length > 0;
      return value !== "" && value !== null && value !== undefined;
    })
  );
}
