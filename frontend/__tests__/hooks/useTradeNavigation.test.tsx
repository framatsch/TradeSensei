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

import React, { useState } from "react";
import { act, cleanup, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useTradeNavigation } from "@/hooks/useTradeNavigation";
import * as tradesHooks from "@/hooks/useTrades";
import { listTradesApiV1PortfoliosPortfolioIdTradesGet } from "@/lib/api/index";
import {
  TRADE_LIST_CONTEXT_KEY,
  readTradeListContext,
  writeTradeListContext,
  type TradeListContext,
} from "@/lib/tradeListContext";
import type { CursorPage, Trade } from "@/lib/types";

const mockRouter = { replace: jest.fn(), push: jest.fn() };

jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));
jest.mock("@/hooks/useActivePortfolio", () => ({ useActivePortfolio: jest.fn() }));
jest.mock("@/lib/api/index", () => ({
  listTradesApiV1PortfoliosPortfolioIdTradesGet: jest.fn(),
}));

const mockActivePortfolio = useActivePortfolio as jest.Mock;
const mockListTrades = listTradesApiV1PortfoliosPortfolioIdTradesGet as jest.Mock;

function makeContext(overrides: Partial<TradeListContext> = {}): TradeListContext {
  return {
    portfolioId: "portfolio-1",
    filters: { status: "closed", pnl_positive: true },
    sort: { sort_by: "pnl", sort_dir: "desc" },
    limit: 20,
    listQuery: "?view_id=swing&pnl_positive=true&sort_by=pnl&sort_dir=desc&limit=20",
    viewName: "Swing A+",
    total: 128,
    pages: [{ cursor: null, ids: ["trade-1", "trade-2", "trade-3"], nextCursor: "cursor-2" }],
    ...overrides,
  };
}

function makeTrade(id: string, symbol = id.toUpperCase()): Trade {
  return {
    id,
    symbol,
    position_id: null,
    direction: "LONG",
    asset_class: "EQUITY",
    is_combo: false,
    multiplier: 1,
    quantity: "10",
    entry_price: "100.00",
    exit_price: "110.00",
    stop_loss: null,
    take_profit: null,
    opened_at: "2026-10-01T10:00:00Z",
    closed_at: "2026-10-02T10:00:00Z",
    pnl: "100.00",
    net_pnl: "99.00",
    commission: "1.00",
    journal: null,
    user_rating: null,
    currency: "USD",
    pnl_eur: null,
    net_pnl_eur: null,
    tradingview_link: null,
    image_urls: [],
    playbook_id: null,
    playbook_name: null,
    account_id: null,
    account_name: null,
    account_type: null,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-02T10:00:00Z",
    is_manually_edited: false,
    tags: [],
    trade_notes: [],
  };
}

function makePage(ids: string[], nextCursor: string | null = null, total: number | null = 128): CursorPage<Trade> {
  return { items: ids.map((id) => makeTrade(id)), next_cursor: nextCursor, total };
}

function response(page: CursorPage<Trade>) {
  return { data: { data: page, meta: {} } };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
}

describe("useTradeNavigation", () => {
  let queryClient: QueryClient;
  let confirmDiscard: jest.SpyInstance;

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  function renderNavigation(id = "trade-2", dirty = false) {
    return renderHook(
      ({ id: tradeId, dirty: isDirty }) => useTradeNavigation(tradeId, { isDirty }),
      { initialProps: { id, dirty }, wrapper: Wrapper },
    );
  }

  function DraftNavigation({ tradeId = "trade-2" }: { tradeId?: string }) {
    const [draft, setDraft] = useState("");
    const navigation = useTradeNavigation(tradeId, { isDirty: draft.length > 0 });
    return <>
      <label>Journal draft<textarea value={draft} onChange={(event) => setDraft(event.target.value)} /></label>
      <button disabled={!navigation.canGoPrev} onClick={navigation.goPrev}>Previous trade</button>
      <button disabled={!navigation.canGoNext} onClick={() => void navigation.goNext()}>Next trade</button>
      {navigation.isLoadingNext && <p role="status">Loading next trades</p>}
    </>;
  }

  beforeEach(() => {
    jest.clearAllMocks();
    mockListTrades.mockReset();
    mockListTrades.mockResolvedValue(response(makePage([])));
    mockActivePortfolio.mockReturnValue({ activePortfolioId: "portfolio-1" });
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
    confirmDiscard = jest.spyOn(window, "confirm").mockReturnValue(true);
    sessionStorage.clear();
    writeTradeListContext(makeContext());
  });

  afterEach(() => {
    cleanup();
    queryClient.clear();
    jest.restoreAllMocks();
    sessionStorage.clear();
  });

  it("replaces history with the previous and next IDs within a page without requesting trades", async () => {
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const { result } = renderNavigation();

    expect(result.current).toMatchObject({
      available: true,
      prevId: "trade-1",
      nextId: "trade-3",
      canGoPrev: true,
      canGoNext: true,
      position: 2,
      total: 128,
    });

    act(() => result.current.goPrev());
    await act(async () => { await result.current.goNext(); });

    expect(mockRouter.replace.mock.calls).toEqual([
      ["/dashboard/trades/trade-1"],
      ["/dashboard/trades/trade-3"],
    ]);
    expect(mockRouter.push).not.toHaveBeenCalled();
    expect(mockListTrades).not.toHaveBeenCalled();
    expect(confirmDiscard).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
  });

  it("uses the previous stored page at its first ID without fetching", () => {
    writeTradeListContext(makeContext({ pages: [
      { cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" },
      { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: "cursor-3" },
    ] }));
    const { result } = renderNavigation("trade-3");

    act(() => result.current.goPrev());

    expect(result.current.prevId).toBe("trade-2");
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-2");
    expect(mockListTrades).not.toHaveBeenCalled();
  });

  it("uses an already stored next page without another request", async () => {
    writeTradeListContext(makeContext({ pages: [
      { cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" },
      { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: null },
    ] }));
    const { result } = renderNavigation("trade-2");

    await act(async () => { await result.current.goNext(); });

    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-3");
    expect(mockListTrades).not.toHaveBeenCalled();
  });

  it("keeps the next-page query disabled until navigation is explicitly requested", () => {
    const useTrades = jest.spyOn(tradesHooks, "useTrades");
    const context = makeContext();
    const { result } = renderNavigation("trade-3");

    expect(result.current.canGoNext).toBe(true);
    expect(result.current.nextId).toBeNull();
    expect(result.current.isLoadingNext).toBe(false);
    expect(mockListTrades).not.toHaveBeenCalled();
    expect(useTrades).toHaveBeenLastCalledWith({
      portfolioId: context.portfolioId,
      cursor: "cursor-2",
      limit: context.limit,
      filters: context.filters,
      sort: context.sort,
      enabled: false,
    });
    expect(useTrades.mock.calls.every(([options]) => options?.enabled === false)).toBe(true);
  });

  it("manually refetches the exact stored query, shares its cache, appends the page, and replaces with its first ID", async () => {
    const context = makeContext({ filters: {
      symbols: ["AAPL", "MSFT"],
      excluded_symbols: ["TSLA"],
      direction: "LONG",
      asset_classes: ["EQUITY"],
      status: "closed",
      pnl_positive: false,
      account_ids: ["account-1"],
      playbook_id: "playbook-1",
      taxonomy_ids: ["tag-1"],
      opened_at_from: "2026-10-01T00:00:00Z",
      closed_at_to: "2026-10-30T23:59:59Z",
      hour_of_day: 0,
      day_of_week: 0,
      annotation_filters: [{ annotation_definition_id: "quality", operator: "eq", value: "A", logic: "and" }],
      execution_state: ["edited"],
      has_unlinked_executions: true,
    } });
    writeTradeListContext(context);
    const page = makePage(["trade-4", "trade-5"], "cursor-3", 130);
    mockListTrades.mockResolvedValueOnce(response(page));
    const useTrades = jest.spyOn(tradesHooks, "useTrades");
    const { result } = renderNavigation("trade-3");

    expect(mockListTrades).not.toHaveBeenCalled();
    await act(async () => { await result.current.goNext(); });

    expect(useTrades).toHaveBeenCalledWith({
      portfolioId: context.portfolioId,
      cursor: "cursor-2",
      limit: context.limit,
      filters: context.filters,
      sort: context.sort,
      enabled: false,
    });
    expect(mockListTrades).toHaveBeenCalledTimes(1);
    expect(mockListTrades).toHaveBeenCalledWith({
      path: { portfolio_id: context.portfolioId },
      query: expect.objectContaining({
        ...context.filters,
        annotation_filters: JSON.stringify(context.filters.annotation_filters),
        cursor: "cursor-2",
        limit: context.limit,
        ...context.sort,
      }),
    });
    expect(queryClient.getQueryData([
      "trades", context.portfolioId, "cursor-2", context.limit, context.filters, context.sort,
    ])).toEqual(page);
    expect(readTradeListContext()).toEqual({
      ...context,
      total: 130,
      pages: [...context.pages, { cursor: "cursor-2", ids: ["trade-4", "trade-5"], nextCursor: "cursor-3" }],
    });
    expect(mockRouter.replace).toHaveBeenCalledTimes(1);
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
    expect(mockRouter.push).not.toHaveBeenCalled();
    expect(result.current.isLoadingNext).toBe(false);
    expect(result.current.navigationError).toBeNull();
    expect(useTrades.mock.calls.every(([options]) => options?.enabled === false)).toBe(true);
  });

  it("exposes loading and ignores repeated next or previous requests while a boundary fetch is pending", async () => {
    const request = deferred<ReturnType<typeof response>>();
    mockListTrades.mockReturnValueOnce(request.promise);
    const { result } = renderNavigation("trade-3");
    let navigation = Promise.resolve();

    act(() => { navigation = result.current.goNext(); });
    await waitFor(() => expect(result.current.isLoadingNext).toBe(true));
    act(() => result.current.goPrev());
    await act(async () => { await result.current.goNext(); });

    expect(mockListTrades).toHaveBeenCalledTimes(1);
    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(readTradeListContext()?.pages).toHaveLength(1);

    await act(async () => {
      request.resolve(response(makePage(["trade-4"])));
      await navigation;
    });

    expect(result.current.isLoadingNext).toBe(false);
    expect(mockRouter.replace).toHaveBeenCalledTimes(1);
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
  });

  it.each([
    ["first", "trade-1", ["trade-1", "trade-2", "trade-3"], false, true],
    ["last", "trade-3", ["trade-1", "trade-2", "trade-3"], true, false],
    ["only", "trade-1", ["trade-1"], false, false],
  ] as const)("disables unavailable directions on the %s trade", async (_label, id, ids, canGoPrev, canGoNext) => {
    writeTradeListContext(makeContext({ pages: [{ cursor: null, ids: [...ids], nextCursor: null }] }));
    const { result } = renderNavigation(id, true);

    expect(result.current).toMatchObject({ available: true, canGoPrev, canGoNext });
    if (!canGoPrev) act(() => result.current.goPrev());
    if (!canGoNext) await act(async () => { await result.current.goNext(); });

    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(mockListTrades).not.toHaveBeenCalled();
    expect(confirmDiscard).not.toHaveBeenCalled();
  });

  it.each<[string, TradeListContext | string | null, string | null, string]>([
    ["no context", null, "portfolio-1", "trade-2"],
    ["malformed context", "{", "portfolio-1", "trade-2"],
    ["another portfolio", makeContext(), "portfolio-2", "trade-2"],
    ["no active portfolio", makeContext(), null, "trade-2"],
    ["an absent trade ID", makeContext(), "portfolio-1", "not-in-list"],
  ])("does not offer navigation for %s", async (_label, context, activePortfolioId, id) => {
    sessionStorage.clear();
    if (typeof context === "string") sessionStorage.setItem(TRADE_LIST_CONTEXT_KEY, context);
    else if (context) writeTradeListContext(context);
    mockActivePortfolio.mockReturnValue({ activePortfolioId });
    const { result } = renderNavigation(id, true);

    expect(result.current).toMatchObject({
      available: false,
      prevId: null,
      nextId: null,
      prevSymbol: null,
      nextSymbol: null,
      canGoPrev: false,
      canGoNext: false,
      position: null,
    });
    act(() => result.current.goPrev());
    await act(async () => { await result.current.goNext(); });

    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(mockListTrades).not.toHaveBeenCalled();
    expect(confirmDiscard).not.toHaveBeenCalled();
    if (activePortfolioId !== "portfolio-1" || !context || typeof context === "string") {
      expect(result.current.backHref).toBe("/dashboard/trades");
    } else {
      expect(result.current.backHref).toBe(`/dashboard/trades${context.listQuery}`);
    }
  });

  it("reports position 25 of 128 for the fifth trade of the second twenty-item page", () => {
    const ids = Array.from({ length: 40 }, (_, index) => `trade-${index + 1}`);
    writeTradeListContext(makeContext({ pages: [
      { cursor: null, ids: ids.slice(0, 20), nextCursor: "cursor-2" },
      { cursor: "cursor-2", ids: ids.slice(20), nextCursor: "cursor-3" },
    ] }));

    const { result } = renderNavigation("trade-25");

    expect(result.current).toMatchObject({ position: 25, total: 128, prevId: "trade-24", nextId: "trade-26" });
  });

  it.each<[string, Partial<TradeListContext>, string]>([
    ["a saved view", {}, "View: Swing A+"],
    ["effective filters", { viewName: null }, "Filtered trade list"],
    ["false and zero-valued filters", { viewName: null, filters: { pnl_positive: false, hour_of_day: 0 } }, "Filtered trade list"],
    ["no filters", { viewName: null, filters: {} }, "All trades"],
    ["empty filter values", { viewName: null, filters: { symbols: [], status: null, direction: "" } }, "All trades"],
  ])("names the source for %s", (_label, context, expected) => {
    writeTradeListContext(makeContext(context));

    const { result } = renderNavigation();

    expect(result.current.sourceLabel).toBe(expected);
  });

  it.each([
    ["?view_id=swing&symbols=AAPL&sort_by=pnl&sort_dir=desc&limit=20", "/dashboard/trades?view_id=swing&symbols=AAPL&sort_by=pnl&sort_dir=desc&limit=20"],
    ["view_id=swing&sort_by=symbol&sort_dir=asc", "/dashboard/trades?view_id=swing&sort_by=symbol&sort_dir=asc"],
    ["", "/dashboard/trades"],
  ])("restores the list URL from %p without duplicating the question mark", (listQuery, backHref) => {
    writeTradeListContext(makeContext({ listQuery }));

    const { result } = renderNavigation();

    expect(result.current.backHref).toBe(backHref);
  });

  it("reads adjacent symbols from the exact list page keys, including the first-page undefined cursor", () => {
    const context = makeContext({ pages: [
      { cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" },
      { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: null },
    ] });
    writeTradeListContext(context);
    queryClient.setQueryData([
      "trades", context.portfolioId, undefined, context.limit, { pnl_positive: true, status: "closed" },
      { sort_dir: "desc", sort_by: "pnl" },
    ], { ...makePage([]), items: [makeTrade("trade-2", "MSFT")] });
    queryClient.setQueryData([
      "trades", context.portfolioId, "cursor-2", context.limit, context.filters, context.sort,
    ], { ...makePage([]), items: [makeTrade("trade-4", "TSLA")] });

    const { result } = renderNavigation("trade-3");

    expect(result.current.prevSymbol).toBe("MSFT");
    expect(result.current.nextSymbol).toBe("TSLA");
    expect(mockListTrades).not.toHaveBeenCalled();
  });

  it("does not borrow symbols from a different portfolio, cursor, page size, filter, or sort", () => {
    const context = makeContext();
    const decoy = { ...makePage([]), items: [makeTrade("trade-1", "WRONG-PREV"), makeTrade("trade-3", "WRONG-NEXT")] };
    const keys = [
      ["trades", "portfolio-2", undefined, context.limit, context.filters, context.sort],
      ["trades", context.portfolioId, "other-cursor", context.limit, context.filters, context.sort],
      ["trades", context.portfolioId, undefined, 50, context.filters, context.sort],
      ["trades", context.portfolioId, undefined, context.limit, { pnl_positive: false }, context.sort],
      ["trades", context.portfolioId, undefined, context.limit, context.filters, { sort_by: "pnl", sort_dir: "asc" }],
    ];
    keys.forEach((key) => queryClient.setQueryData(key, decoy));

    const { result } = renderNavigation();

    expect(result.current.prevSymbol).toBeNull();
    expect(result.current.nextSymbol).toBeNull();
    expect(mockListTrades).not.toHaveBeenCalled();
  });

  it("keeps the unsaved draft and context intact when either within-page dirty confirmation is cancelled", async () => {
    confirmDiscard.mockReturnValue(false);
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const user = userEvent.setup();
    render(<DraftNavigation />, { wrapper: Wrapper });
    const journal = screen.getByRole("textbox", { name: "Journal draft" });

    await user.type(journal, "Waited for the retest before entering.");
    await user.click(screen.getByRole("button", { name: "Previous trade" }));
    await user.click(screen.getByRole("button", { name: "Next trade" }));

    expect(confirmDiscard).toHaveBeenCalledTimes(2);
    expect(confirmDiscard).toHaveBeenNthCalledWith(1, "Discard unsaved changes to this trade?");
    expect(confirmDiscard).toHaveBeenNthCalledWith(2, "Discard unsaved changes to this trade?");
    expect(journal).toHaveValue("Waited for the retest before entering.");
    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(mockListTrades).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
  });

  it.each(["previous", "next"] as const)("navigates %s within the page after accepting the dirty confirmation", async (direction) => {
    const { result } = renderNavigation("trade-2", true);

    await act(async () => {
      if (direction === "previous") result.current.goPrev();
      else await result.current.goNext();
    });

    expect(confirmDiscard).toHaveBeenCalledWith("Discard unsaved changes to this trade?");
    expect(mockRouter.replace).toHaveBeenCalledWith(`/dashboard/trades/${direction === "previous" ? "trade-1" : "trade-3"}`);
    expect(mockListTrades).not.toHaveBeenCalled();
  });

  it("confirms existing dirty changes after the boundary response and before appending or navigating", async () => {
    const request = deferred<ReturnType<typeof response>>();
    mockListTrades.mockReturnValueOnce(request.promise);
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const setItem = jest.spyOn(Storage.prototype, "setItem");
    const { result } = renderNavigation("trade-3", true);
    let navigation = Promise.resolve();

    act(() => { navigation = result.current.goNext(); });
    await waitFor(() => expect(result.current.isLoadingNext).toBe(true));

    expect(mockListTrades).toHaveBeenCalledTimes(1);
    expect(confirmDiscard).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(mockRouter.replace).not.toHaveBeenCalled();
    confirmDiscard.mockImplementation(() => {
      expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
      expect(mockRouter.replace).not.toHaveBeenCalled();
      return true;
    });

    await act(async () => {
      request.resolve(response(makePage(["trade-4"])));
      await navigation;
    });

    expect(confirmDiscard).toHaveBeenCalledWith("Discard unsaved changes to this trade?");
    expect(setItem).toHaveBeenCalledTimes(1);
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
  });

  it.each([false, true])("protects a journal edited while the next page is pending when confirmation is %s", async (accepted) => {
    const request = deferred<ReturnType<typeof response>>();
    mockListTrades.mockReturnValueOnce(request.promise);
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const setItem = jest.spyOn(Storage.prototype, "setItem");
    const user = userEvent.setup();
    render(<DraftNavigation tradeId="trade-3" />, { wrapper: Wrapper });
    const journal = screen.getByRole("textbox", { name: "Journal draft" });

    await user.click(screen.getByRole("button", { name: "Next trade" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Loading next trades");
    expect(mockListTrades).toHaveBeenCalledTimes(1);
    expect(confirmDiscard).not.toHaveBeenCalled();
    await user.type(journal, "New journal draft written while loading.");

    expect(setItem).not.toHaveBeenCalled();
    expect(mockRouter.replace).not.toHaveBeenCalled();
    confirmDiscard.mockImplementation(() => {
      expect(journal).toHaveValue("New journal draft written while loading.");
      expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
      expect(setItem).not.toHaveBeenCalled();
      expect(mockRouter.replace).not.toHaveBeenCalled();
      return accepted;
    });

    await act(async () => { request.resolve(response(makePage(["trade-4"]))); });
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());

    expect(confirmDiscard).toHaveBeenCalledTimes(1);
    expect(confirmDiscard).toHaveBeenCalledWith("Discard unsaved changes to this trade?");
    expect(journal).toHaveValue("New journal draft written while loading.");
    expect(mockListTrades).toHaveBeenCalledTimes(1);
    if (accepted) {
      expect(mockRouter.replace).toHaveBeenCalledTimes(1);
      expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
      expect(setItem).toHaveBeenCalledTimes(1);
      expect(readTradeListContext()?.pages).toEqual([
        makeContext().pages[0],
        { cursor: "cursor-2", ids: ["trade-4"], nextCursor: null },
      ]);
    } else {
      expect(mockRouter.replace).not.toHaveBeenCalled();
      expect(setItem).not.toHaveBeenCalled();
      expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
    }
  });

  it("reports an API failure without changing the context and retries only on another next action", async () => {
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    mockListTrades.mockResolvedValueOnce({ data: null, error: new Error("Offline") });
    const { result } = renderNavigation("trade-3");

    await act(async () => { await result.current.goNext(); });

    expect(result.current).toMatchObject({
      navigationError: "Could not load the next trades. Please try again.",
      isLoadingNext: false,
      canGoNext: true,
    });
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(mockListTrades).toHaveBeenCalledTimes(1);

    mockListTrades.mockResolvedValueOnce(response(makePage(["trade-4"], null, null)));
    await act(async () => { await result.current.goNext(); });

    expect(mockListTrades).toHaveBeenCalledTimes(2);
    expect(result.current.navigationError).toBeNull();
    expect(result.current.isLoadingNext).toBe(false);
    expect(readTradeListContext()?.total).toBe(128);
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
  });

  it("also allows retry after refetch itself rejects or returns no page", async () => {
    type TradesQuery = ReturnType<typeof tradesHooks.useTrades>;
    const useRealTrades = tradesHooks.useTrades;
    let currentQuery: TradesQuery;
    const refetch = jest.fn<ReturnType<TradesQuery["refetch"]>, Parameters<TradesQuery["refetch"]>>()
      .mockRejectedValueOnce(new Error("Refetch rejected"))
      .mockImplementationOnce(async () => currentQuery)
      .mockImplementation((options) => currentQuery.refetch(options));
    jest.spyOn(tradesHooks, "useTrades").mockImplementation(function useTestTrades(options) {
      currentQuery = useRealTrades(options);
      return { ...currentQuery, refetch };
    });
    mockListTrades.mockResolvedValueOnce(response(makePage(["trade-4"])));
    const { result } = renderNavigation("trade-3");

    for (let attempt = 0; attempt < 2; attempt += 1) {
      await act(async () => { await result.current.goNext(); });
      expect(result.current.navigationError).toBe("Could not load the next trades. Please try again.");
      expect(result.current.isLoadingNext).toBe(false);
      expect(mockRouter.replace).not.toHaveBeenCalled();
      expect(readTradeListContext()?.pages).toHaveLength(1);
    }
    await act(async () => { await result.current.goNext(); });

    expect(refetch).toHaveBeenCalledTimes(3);
    expect(result.current.navigationError).toBeNull();
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades/trade-4");
  });

  it("handles an empty final page by disabling next without navigating to an undefined ID", async () => {
    mockListTrades.mockResolvedValueOnce(response(makePage([], null, null)));
    const { result } = renderNavigation("trade-3");

    await act(async () => { await result.current.goNext(); });

    expect(result.current.canGoNext).toBe(false);
    expect(result.current.navigationError).toBeNull();
    expect(readTradeListContext()).toMatchObject({
      total: 128,
      pages: [makeContext().pages[0], { cursor: "cursor-2", ids: [], nextCursor: null }],
    });
    expect(mockRouter.replace).not.toHaveBeenCalled();
  });

  it.each(["trade", "portfolio"] as const)("ignores a late next-page response after the active %s changes", async (changed) => {
    const request = deferred<ReturnType<typeof response>>();
    mockListTrades.mockReturnValueOnce(request.promise);
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const { result, rerender } = renderNavigation("trade-3");
    let navigation = Promise.resolve();
    act(() => { navigation = result.current.goNext(); });
    await waitFor(() => expect(result.current.isLoadingNext).toBe(true));

    if (changed === "portfolio") mockActivePortfolio.mockReturnValue({ activePortfolioId: "portfolio-2" });
    rerender({ id: changed === "trade" ? "trade-1" : "trade-3", dirty: false });
    await act(async () => {
      request.resolve(response(makePage(["trade-4"])));
      await navigation;
    });

    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
    expect(result.current.isLoadingNext).toBe(false);
    expect(result.current.navigationError).toBeNull();
  });

  it("ignores a deferred boundary response after unmount without confirming, storing, or navigating", async () => {
    const request = deferred<ReturnType<typeof response>>();
    mockListTrades.mockReturnValueOnce(request.promise);
    const stored = sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY);
    const setItem = jest.spyOn(Storage.prototype, "setItem");
    const { result, unmount } = renderNavigation("trade-3", true);
    let navigation = Promise.resolve();
    act(() => { navigation = result.current.goNext(); });
    await waitFor(() => expect(result.current.isLoadingNext).toBe(true));
    expect(mockListTrades).toHaveBeenCalledTimes(1);

    unmount();
    await act(async () => {
      request.resolve(response(makePage(["trade-4"])));
      await navigation;
    });

    expect(confirmDiscard).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBe(stored);
    expect(mockRouter.replace).not.toHaveBeenCalled();
  });
});
