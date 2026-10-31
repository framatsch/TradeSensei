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

import { z } from "zod";
import type { TradeFilters, TradeSortConfig } from "@/hooks/useTrades";

export const TRADE_LIST_CONTEXT_KEY = "tradesensei.tradeListContext";

export interface TradeListPage {
  cursor: string | null;
  ids: string[];
  nextCursor: string | null;
}

export interface TradeListContext {
  portfolioId: string;
  filters: TradeFilters;
  sort: TradeSortConfig;
  limit: number;
  listQuery: string;
  viewName: string | null;
  total: number | null;
  pages: TradeListPage[];
}

const contextSchema: z.ZodType<TradeListContext> = z.object({
  portfolioId: z.string().min(1),
  filters: z.object({
    symbols: z.array(z.string()).optional(),
    excluded_symbols: z.array(z.string()).optional(),
    direction: z.string().optional(),
    asset_classes: z.array(z.string()).optional(),
    opened_at_from: z.string().optional(),
    opened_at_to: z.string().optional(),
    closed_at_from: z.string().optional(),
    closed_at_to: z.string().optional(),
    taxonomy_ids: z.array(z.string()).optional(),
    playbook_id: z.string().optional(),
    pnl_positive: z.boolean().nullable().optional(),
    status: z.enum(["open", "closed"]).nullable().optional(),
    account_ids: z.array(z.string()).optional(),
    hour_of_day: z.number().int().min(0).max(23).optional(),
    day_of_week: z.number().int().min(0).max(6).optional(),
    annotation_filters: z.array(z.object({
      annotation_definition_id: z.string(),
      operator: z.string(),
      value: z.union([z.string(), z.number(), z.boolean()]),
      logic: z.enum(["and", "or"]),
      _key: z.string().optional(),
    })).optional(),
    execution_state: z.array(z.enum(["manual", "edited", "imported"])).optional(),
    has_unlinked_executions: z.boolean().optional(),
  }),
  sort: z.object({
    sort_by: z.string().optional(),
    sort_dir: z.enum(["asc", "desc"]).optional(),
  }),
  limit: z.number().int().positive(),
  listQuery: z.string(),
  viewName: z.string().nullable(),
  total: z.number().int().nonnegative().nullable(),
  pages: z.array(z.object({
    cursor: z.string().nullable(),
    ids: z.array(z.string().min(1)),
    nextCursor: z.string().nullable(),
  })),
});

export function readTradeListContext(): TradeListContext | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = window.sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    if (!stored) return null;
    const result = contextSchema.safeParse(JSON.parse(stored));
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}

export function writeTradeListContext(context: TradeListContext): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(TRADE_LIST_CONTEXT_KEY, JSON.stringify(context));
  } catch {
    // Navigation remains optional when browser storage is unavailable or full.
  }
}

type TradeListQuery = Pick<TradeListContext, "portfolioId" | "filters" | "sort" | "limit">;

function sortedKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortedKeys);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b))
      .map(([key, item]) => [key, sortedKeys(item)]));
  }
  return value;
}

export function isSameQuery(a: TradeListQuery, b: TradeListQuery): boolean {
  const query = ({ portfolioId, filters, sort, limit }: TradeListQuery) =>
    sortedKeys({ portfolioId, filters, sort, limit });
  return JSON.stringify(query(a)) === JSON.stringify(query(b));
}

export function upsertPage(
  context: TradeListContext,
  pageIndex: number,
  page: TradeListPage,
): TradeListContext {
  // Later cursors may be stale after a refetch changes this page's membership.
  const previous = context.pages[pageIndex];
  const unchanged = previous?.cursor === page.cursor &&
    previous.nextCursor === page.nextCursor &&
    JSON.stringify(previous.ids) === JSON.stringify(page.ids);
  const pages = context.pages.slice(0, unchanged ? undefined : pageIndex + 1);
  pages[pageIndex] = page;
  return { ...context, pages };
}
