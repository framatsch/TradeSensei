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
import { countActiveFilters, DESKTOP_FILTER_FIELDS, FILTER_GROUPS } from "@/lib/tradeFilterFields";

describe("trade filter field registry", () => {
  it("assigns every desktop field to exactly one mobile group", () => {
    const groupedFields = Object.values(FILTER_GROUPS).flat();
    expect(groupedFields).toHaveLength(DESKTOP_FILTER_FIELDS.length);
    expect(new Set(groupedFields)).toEqual(new Set(DESKTOP_FILTER_FIELDS));
    for (const field of DESKTOP_FILTER_FIELDS) {
      expect(groupedFields.filter((key) => key === field)).toHaveLength(1);
    }
  });

  it("counts every active filter consistently across groups, including false and zero", () => {
    const filters: Required<TradeFilters> = {
      symbols: ["AAPL"],
      excluded_symbols: ["TSLA"],
      direction: "LONG",
      status: "closed",
      pnl_positive: false,
      asset_classes: ["EQUITY"],
      opened_at_from: "2026-10-01",
      opened_at_to: "2026-10-02",
      closed_at_from: "2026-10-03",
      closed_at_to: "2026-10-04",
      hour_of_day: 0,
      day_of_week: 0,
      playbook_id: "playbook-1",
      taxonomy_ids: ["taxonomy-1"],
      annotation_filters: [{ annotation_definition_id: "definition-1", operator: "eq", value: false, logic: "and" }],
      account_ids: ["account-1"],
      execution_state: ["manual"],
      has_unlinked_executions: true,
    };

    expect(countActiveFilters(filters, FILTER_GROUPS.trade)).toBe(6);
    expect(countActiveFilters(filters, FILTER_GROUPS.time)).toBe(6);
    expect(countActiveFilters(filters, FILTER_GROUPS.journal)).toBe(3);
    expect(countActiveFilters(filters, FILTER_GROUPS.account)).toBe(3);
    expect(countActiveFilters(filters)).toBe(18);
    expect(Object.values(FILTER_GROUPS).reduce((total, keys) => total + countActiveFilters(filters, keys), 0)).toBe(countActiveFilters(filters));
  });

  it("does not count empty, null, or undefined filter values", () => {
    expect(countActiveFilters({ symbols: [], excluded_symbols: [], direction: "", status: null, pnl_positive: null, account_ids: [], annotation_filters: [] })).toBe(0);
  });
});
