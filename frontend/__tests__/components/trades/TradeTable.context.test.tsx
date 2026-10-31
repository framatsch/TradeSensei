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

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeTable } from "@/components/trades/TradeTable";
import { useTrades } from "@/hooks/useTrades";
import {
  TRADE_LIST_CONTEXT_KEY,
  readTradeListContext,
  writeTradeListContext,
  type TradeListContext,
} from "@/lib/tradeListContext";

jest.mock("@/hooks/useTrades", () => ({ useTrades: jest.fn() }));
jest.mock("@/hooks/useFeatureFlag", () => ({ __esModule: true, default: () => false }));
jest.mock("@/components/trades/TradeRow", () => ({
  TradeRow: ({ trade }: { trade: { symbol: string } }) => <tr><td>{trade.symbol}</td></tr>,
}));
jest.mock("@/components/trades/TradeCard", () => ({
  TradeCard: ({ trade }: { trade: { symbol: string } }) => <div>{trade.symbol}</div>,
}));

type Props = React.ComponentProps<typeof TradeTable>;

const mockUseTrades = useTrades as jest.Mock;

function makePage(ids: string[], nextCursor: string | null, total: number | null = 128) {
  return { items: ids.map((id) => ({ id, symbol: id.toUpperCase() })), next_cursor: nextCursor, total };
}

const props: Props = {
  portfolioId: "portfolio-1",
  filters: { status: "closed", pnl_positive: true },
  sort: { sort_by: "pnl", sort_dir: "desc" },
  limit: 20,
  listQuery: "view_id=swing&pnl_positive=true&sort_by=pnl&sort_dir=desc&limit=20",
  viewName: "Swing A+",
};

function expectedContext(overrides: Partial<TradeListContext> = {}): TradeListContext {
  return {
    portfolioId: "portfolio-1",
    filters: props.filters!,
    sort: props.sort!,
    limit: 20,
    listQuery: props.listQuery!,
    viewName: "Swing A+",
    total: 128,
    pages: [{ cursor: null, ids: ["trade-1", "trade-2"], nextCursor: "cursor-2" }],
    ...overrides,
  };
}

describe("TradeTable list context persistence", () => {
  let pages: Record<string, ReturnType<typeof makePage>>;

  beforeEach(() => {
    sessionStorage.clear();
    mockUseTrades.mockReset();
    pages = {
      first: makePage(["trade-1", "trade-2"], "cursor-2"),
      "cursor-2": makePage(["trade-3", "trade-4"], "cursor-3"),
      "cursor-3": makePage(["trade-5", "trade-6"], null),
    };
    mockUseTrades.mockImplementation(({ cursor }) => ({
      data: pages[cursor ?? "first"],
      isLoading: false,
      isError: false,
      isPlaceholderData: false,
      error: null,
      refetch: jest.fn(),
    }));
  });

  afterEach(() => {
    jest.restoreAllMocks();
    sessionStorage.clear();
  });

  it("stores the effective query, saved view, total, and page-one IDs when data arrives", () => {
    render(<TradeTable {...props} />);

    expect(readTradeListContext()).toEqual(expectedContext());
    expect(mockUseTrades).toHaveBeenLastCalledWith({
      portfolioId: props.portfolioId,
      filters: props.filters,
      sort: props.sort,
      limit: props.limit,
      cursor: undefined,
    });
  });

  it("appends further pages of the same query and retains them on an unchanged page refetch", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<TradeTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));

    const twoPages = expectedContext({ pages: [
      expectedContext().pages[0],
      { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: "cursor-3" },
    ] });
    expect(readTradeListContext()).toEqual(twoPages);

    await user.click(screen.getByRole("button", { name: "‹ Prev" }));
    pages.first = { ...pages.first, items: [...pages.first.items] };
    rerender(<TradeTable {...props} listQuery="view_id=renamed" viewName="Renamed view" />);

    expect(readTradeListContext()).toEqual({ ...twoPages, listQuery: "view_id=renamed", viewName: "Renamed view" });
  });

  it.each<[string, Partial<Props>]>([
    ["effective filters", { filters: { status: "open", pnl_positive: false } }],
    ["sort", { sort: { sort_by: "symbol", sort_dir: "asc" } }],
    ["page size", { limit: 50 }],
    ["portfolio", { portfolioId: "portfolio-2" }],
  ])("replaces a three-page context and resets the cursor when %s changes", async (_label, change) => {
    const user = userEvent.setup();
    const { rerender } = render(<TradeTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    expect(readTradeListContext()?.pages).toHaveLength(3);

    pages.first = makePage(["new-trade"], "new-cursor", 17);
    mockUseTrades.mockClear();
    const nextProps = { ...props, ...change };
    rerender(<TradeTable {...nextProps} />);

    await waitFor(() => expect(readTradeListContext()).toEqual({
      ...expectedContext(),
      portfolioId: nextProps.portfolioId,
      filters: nextProps.filters,
      sort: nextProps.sort,
      limit: nextProps.limit,
      total: 17,
      pages: [{ cursor: null, ids: ["new-trade"], nextCursor: "new-cursor" }],
    }));
    expect(mockUseTrades.mock.calls.every(([options]) => options.cursor === undefined)).toBe(true);
  });

  it("upserts changed IDs for a refetched page and discards all later cursor pages", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<TradeTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    await user.click(screen.getByRole("button", { name: "‹ Prev" }));
    expect(readTradeListContext()?.pages).toHaveLength(3);

    pages["cursor-2"] = makePage(["replacement", "trade-4"], "replacement-next", 127);
    rerender(<TradeTable {...props} />);

    expect(readTradeListContext()).toEqual(expectedContext({
      total: 127,
      pages: [
        expectedContext().pages[0],
        { cursor: "cursor-2", ids: ["replacement", "trade-4"], nextCursor: "replacement-next" },
      ],
    }));
  });

  it.each(["loading", "error", "placeholder", "missing data", "missing portfolio"] as const)
  ("does not overwrite a valid context with %s results", (state) => {
    const previous = expectedContext();
    writeTradeListContext(previous);
    mockUseTrades.mockReturnValue({
      data: state === "missing data" ? undefined : makePage(["uncommitted"], null),
      isLoading: state === "loading",
      isError: state === "error",
      isPlaceholderData: state === "placeholder",
      error: new Error("Unavailable"),
      refetch: jest.fn(),
    });

    render(<TradeTable {...props} portfolioId={state === "missing portfolio" ? undefined : props.portfolioId} />);

    expect(readTradeListContext()).toEqual(previous);
  });

  it("does not write a page whose stored predecessor no longer leads to its cursor", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<TradeTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    const invalidated = expectedContext({ pages: [{ cursor: null, ids: ["replacement"], nextCursor: "different-cursor" }] });
    writeTradeListContext(invalidated);
    pages["cursor-2"] = makePage(["stale-trade"], "cursor-3");

    rerender(<TradeTable {...props} />);

    expect(readTradeListContext()).toEqual(invalidated);
  });

  it("keeps loaded pages in memory when storage is denied, then persists a contiguous context when it recovers", async () => {
    const user = userEvent.setup();
    const denied = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("SecurityError"); });
    const { rerender } = render(<TradeTable {...props} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));
    expect(sessionStorage.getItem(TRADE_LIST_CONTEXT_KEY)).toBeNull();
    denied.mockRestore();

    rerender(<TradeTable {...props} listQuery="view_id=recovered" />);

    expect(readTradeListContext()).toEqual(expectedContext({
      listQuery: "view_id=recovered",
      pages: [
        expectedContext().pages[0],
        { cursor: "cursor-2", ids: ["trade-3", "trade-4"], nextCursor: "cursor-3" },
      ],
    }));
  });
});
