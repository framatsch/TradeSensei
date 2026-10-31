/** @jest-environment node */

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

import {
  TRADE_LIST_CONTEXT_KEY,
  isSameQuery,
  readTradeListContext,
  upsertPage,
  writeTradeListContext,
  type TradeListContext,
  type TradeListPage,
} from "@/lib/tradeListContext";

function makeContext(overrides: Partial<TradeListContext> = {}): TradeListContext {
  return {
    portfolioId: "portfolio-1",
    filters: { status: "closed", pnl_positive: true },
    sort: { sort_by: "pnl", sort_dir: "desc" },
    limit: 20,
    listQuery: "view_id=swing&pnl_positive=true&sort_by=pnl&sort_dir=desc&limit=20",
    viewName: "Swing A+",
    total: 128,
    pages: [{ cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" }],
    ...overrides,
  };
}

describe("trade list context storage", () => {
  const values = new Map<string, string>();
  const storage = {
    getItem: jest.fn((key: string) => values.get(key) ?? null),
    setItem: jest.fn((key: string, value: string) => { values.set(key, value); }),
  };

  beforeEach(() => {
    values.clear();
    storage.getItem.mockClear();
    storage.setItem.mockClear();
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: { sessionStorage: storage },
    });
  });

  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
    jest.restoreAllMocks();
  });

  it("round-trips the complete effective query and ordered pages using the tab-scoped key", () => {
    const context = makeContext({
      filters: {
        symbols: ["AAPL", "MSFT"],
        excluded_symbols: ["TSLA"],
        direction: "LONG",
        asset_classes: ["EQUITY", "COMBO"],
        opened_at_from: "2026-10-01",
        opened_at_to: "2026-10-10",
        closed_at_from: "2026-10-11",
        closed_at_to: "2026-10-30",
        taxonomy_ids: ["tag-1"],
        playbook_id: "playbook-1",
        pnl_positive: false,
        status: "closed",
        account_ids: ["account-1"],
        hour_of_day: 0,
        day_of_week: 0,
        annotation_filters: [{
          annotation_definition_id: "quality",
          operator: "eq",
          value: 4,
          logic: "and",
          _key: "draft-row-1",
        }],
        execution_state: ["edited", "imported"],
        has_unlinked_executions: false,
      },
      pages: [
        { cursor: null, ids: ["trade-2", "trade-1"], nextCursor: "cursor-2" },
        { cursor: "cursor-2", ids: ["trade-3"], nextCursor: null },
      ],
    });

    writeTradeListContext(context);

    expect(TRADE_LIST_CONTEXT_KEY).toBe("tradesensei.tradeListContext");
    expect(storage.setItem).toHaveBeenCalledWith(TRADE_LIST_CONTEXT_KEY, JSON.stringify(context));
    expect(readTradeListContext()).toEqual(context);
    expect(storage.getItem).toHaveBeenCalledWith(TRADE_LIST_CONTEXT_KEY);
  });

  it("accepts unknown totals, no saved view, and an empty loaded page", () => {
    const context = makeContext({
      total: null,
      viewName: null,
      filters: {},
      sort: {},
      pages: [{ cursor: null, ids: [], nextCursor: null }],
    });

    writeTradeListContext(context);

    expect(readTradeListContext()).toEqual(context);
  });

  it("returns null when the tab has no stored context", () => {
    expect(readTradeListContext()).toBeNull();
  });

  it.each(["", "{", "not JSON", '{"pages":'])
  ("ignores malformed JSON %p", (stored) => {
    values.set(TRADE_LIST_CONTEXT_KEY, stored);

    expect(readTradeListContext()).toBeNull();
  });

  it.each([
    ["null", null],
    ["an array", []],
    ["missing fields", {}],
    ["an empty portfolio ID", makeContext({ portfolioId: "" })],
    ["missing filters", { ...makeContext(), filters: null }],
    ["a symbol scalar", { ...makeContext(), filters: { symbols: "AAPL" } }],
    ["a string boolean", { ...makeContext(), filters: { pnl_positive: "false" } }],
    ["an invalid status", { ...makeContext(), filters: { status: "all" } }],
    ["an invalid hour", { ...makeContext(), filters: { hour_of_day: 24 } }],
    ["an invalid weekday", { ...makeContext(), filters: { day_of_week: -1 } }],
    ["an invalid execution state", { ...makeContext(), filters: { execution_state: ["unknown"] } }],
    ["an invalid annotation", { ...makeContext(), filters: { annotation_filters: [{ value: [] }] } }],
    ["an invalid sort direction", { ...makeContext(), sort: { sort_dir: "sideways" } }],
    ["a zero page size", makeContext({ limit: 0 })],
    ["a fractional page size", makeContext({ limit: 1.5 })],
    ["a negative total", makeContext({ total: -1 })],
    ["a nonnumeric total", { ...makeContext(), total: "128" }],
    ["an invalid saved view", { ...makeContext(), viewName: false }],
    ["missing pages", { ...makeContext(), pages: null }],
    ["a numeric cursor", { ...makeContext(), pages: [{ cursor: 1, ids: [], nextCursor: null }] }],
    ["an empty trade ID", makeContext({ pages: [{ cursor: null, ids: [""], nextCursor: null }] })],
    ["a numeric trade ID", { ...makeContext(), pages: [{ cursor: null, ids: [1], nextCursor: null }] }],
    ["an invalid next cursor", { ...makeContext(), pages: [{ cursor: null, ids: [], nextCursor: false }] }],
  ])("ignores valid JSON with %s", (_description, stored) => {
    values.set(TRADE_LIST_CONTEXT_KEY, JSON.stringify(stored));

    expect(readTradeListContext()).toBeNull();
  });

  it("does not access browser storage during SSR", () => {
    Reflect.deleteProperty(globalThis, "window");

    expect(readTradeListContext()).toBeNull();
    expect(() => writeTradeListContext(makeContext())).not.toThrow();
    expect(storage.getItem).not.toHaveBeenCalled();
    expect(storage.setItem).not.toHaveBeenCalled();
  });

  it("returns null when accessing sessionStorage is denied", () => {
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: { get sessionStorage() { throw new Error("SecurityError"); } },
    });

    expect(readTradeListContext()).toBeNull();
    expect(() => writeTradeListContext(makeContext())).not.toThrow();
  });

  it("returns null when storage reads fail", () => {
    storage.getItem.mockImplementationOnce(() => { throw new Error("SecurityError"); });

    expect(readTradeListContext()).toBeNull();
  });

  it("keeps navigation optional when storage is full", () => {
    storage.setItem.mockImplementationOnce(() => { throw new Error("QuotaExceededError"); });

    expect(() => writeTradeListContext(makeContext())).not.toThrow();
    expect(values.has(TRADE_LIST_CONTEXT_KEY)).toBe(false);
  });
});

describe("isSameQuery", () => {
  it("treats recursively reordered object keys as the same query", () => {
    const first = makeContext({
      filters: {
        status: "closed",
        symbols: ["AAPL", "MSFT"],
        annotation_filters: [{ annotation_definition_id: "quality", operator: "eq", value: 4, logic: "and" }],
      },
    });
    const reordered = makeContext({
      sort: { sort_dir: "desc", sort_by: "pnl" },
      filters: {
        annotation_filters: [{ logic: "and", value: 4, operator: "eq", annotation_definition_id: "quality" }],
        symbols: ["AAPL", "MSFT"],
        status: "closed",
      },
    });

    expect(isSameQuery(first, reordered)).toBe(true);
  });

  it("ignores list presentation metadata and loaded pages when deciding whether to replace", () => {
    const original = makeContext();
    const sameQuery = makeContext({ listQuery: "view_id=another", viewName: "Renamed", total: 3, pages: [] });

    expect(isSameQuery(original, sameQuery)).toBe(true);
  });

  it.each<[string, Partial<TradeListContext>]>([
    ["portfolio", { portfolioId: "portfolio-2" }],
    ["filters", { filters: { status: "open", pnl_positive: true } }],
    ["sort field", { sort: { sort_by: "symbol", sort_dir: "desc" } }],
    ["sort direction", { sort: { sort_by: "pnl", sort_dir: "asc" } }],
    ["page size", { limit: 50 }],
  ])("requires replacement when the %s changes", (_description, change) => {
    expect(isSameQuery(makeContext(), makeContext(change))).toBe(false);
  });

  it("does not reorder filter array values while comparing queries", () => {
    const first = makeContext({ filters: { symbols: ["AAPL", "MSFT"] } });
    const reordered = makeContext({ filters: { symbols: ["MSFT", "AAPL"] } });

    expect(isSameQuery(first, reordered)).toBe(false);
  });
});

describe("upsertPage", () => {
  const first: TradeListPage = { cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" };
  const second: TradeListPage = { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: "cursor-3" };
  const third: TradeListPage = { cursor: "cursor-3", ids: ["trade-5"], nextCursor: null };

  it("creates page one in a fresh context without changing the input", () => {
    const context = makeContext({ pages: [] });

    const updated = upsertPage(context, 0, first);

    expect(updated).toEqual({ ...context, pages: [first] });
    expect(context.pages).toEqual([]);
    expect(updated).not.toBe(context);
  });

  it("appends subsequent pages instead of replacing the previously loaded IDs", () => {
    const context = makeContext({ pages: [first] });
    Object.freeze(context.pages);

    const updated = upsertPage(context, 1, second);

    expect(updated).toEqual({ ...context, pages: [first, second] });
    expect(context.pages).toEqual([first]);
  });

  it("preserves later pages when a refetch has identical IDs and cursors", () => {
    const context = makeContext({ pages: [first, second, third] });

    const updated = upsertPage(context, 1, { ...second, ids: [...second.ids] });

    expect(updated.pages).toEqual([first, second, third]);
    expect(updated.pages).not.toBe(context.pages);
  });

  it.each<[string, Partial<TradeListPage>]>([
    ["membership", { ids: ["replacement", "trade-4"] }],
    ["ID order", { ids: ["trade-4", "trade-3"] }],
    ["the current cursor", { cursor: "replacement-cursor" }],
    ["the next cursor", { nextCursor: "replacement-next-cursor" }],
  ])("invalidates later pages when %s changes", (_description, change) => {
    const context = makeContext({ pages: [first, second, third] });
    const replacement = { ...second, ...change };

    const updated = upsertPage(context, 1, replacement);

    expect(updated.pages).toEqual([first, replacement]);
    expect(context.pages).toEqual([first, second, third]);
  });

  it("drops every later page when the first page changes", () => {
    const context = makeContext({ pages: [first, second, third] });
    const replacement = { ...first, ids: ["new-first-trade"] };

    expect(upsertPage(context, 0, replacement).pages).toEqual([replacement]);
  });
});
