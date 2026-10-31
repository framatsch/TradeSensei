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

import type { TradeFilters } from "@/hooks/useTrades";

/** Symbol inclusion and exclusion share a single rendered field. */
export type FilterFieldKey = Exclude<keyof TradeFilters, "excluded_symbols">;
export type FilterGroupKey = "trade" | "time" | "journal" | "account";

export const DESKTOP_FILTER_FIELDS: readonly FilterFieldKey[] = [
  "symbols",
  "direction",
  "status",
  "opened_at_from",
  "opened_at_to",
  "closed_at_from",
  "closed_at_to",
  "hour_of_day",
  "day_of_week",
  "account_ids",
  "playbook_id",
  "pnl_positive",
  "asset_classes",
  "execution_state",
  "has_unlinked_executions",
  "taxonomy_ids",
  "annotation_filters",
];

export const FILTER_GROUPS: Record<FilterGroupKey, readonly FilterFieldKey[]> = {
  trade: ["symbols", "direction", "status", "pnl_positive", "asset_classes"],
  time: ["opened_at_from", "opened_at_to", "closed_at_from", "closed_at_to", "hour_of_day", "day_of_week"],
  journal: ["playbook_id", "taxonomy_ids", "annotation_filters"],
  account: ["account_ids", "execution_state", "has_unlinked_executions"],
};

/** Preserve desktop counting, including false/zero and both symbol lists. */
export function countActiveFilters(
  filters: TradeFilters,
  keys: readonly FilterFieldKey[] = DESKTOP_FILTER_FIELDS,
): number {
  return keys.reduce((count, key) => {
    if (key === "symbols") {
      return count + Number(!!filters.symbols?.length) + Number(!!filters.excluded_symbols?.length);
    }
    const value = filters[key];
    const active = Array.isArray(value)
      ? value.length > 0
      : value !== undefined && value !== null && value !== "";
    return count + Number(active);
  }, 0);
}
