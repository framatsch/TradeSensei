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
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeTable } from "@/components/trades/TradeTable";
import type { UseTradesOptions } from "@/hooks/useTrades";
import type { CursorPage, Trade } from "@/lib/types";

const mockUseTrades = jest.fn();
const mockRefetch = jest.fn();

jest.mock("@/hooks/useTrades", () => ({ useTrades: (options: UseTradesOptions) => mockUseTrades(options) }));
jest.mock("@/hooks/useFeatureFlag", () => ({ __esModule: true, default: () => false }));
jest.mock("@/hooks/useNotes", () => ({ useAddNote: jest.fn() }));

const trade: Trade = {
  id: "trade-1", position_id: null, symbol: "AAPL", direction: "LONG", asset_class: "EQUITY",
  is_combo: false, multiplier: 1, quantity: "10", entry_price: "100", exit_price: "110",
  stop_loss: null, take_profit: null, opened_at: "2026-10-24T12:00:00Z", closed_at: "2026-10-25T12:00:00Z",
  pnl: "100", net_pnl: "99", commission: "1", journal: null, user_rating: null, currency: "USD",
  pnl_eur: null, net_pnl_eur: null, tradingview_link: null, image_urls: [], playbook_id: null, playbook_name: null,
  account_id: "account-1", account_name: "IBKR Main", account_type: "ibkr", tags: [], trade_notes: [],
  created_at: "2026-10-24T12:00:00Z", updated_at: "2026-10-25T12:00:00Z", is_manually_edited: false,
};
const firstPage: CursorPage<Trade> = {
  items: [trade, { ...trade, id: "trade-2", symbol: "MSFT" }], total: 3, next_cursor: "cursor-2",
};
const lastPage: CursorPage<Trade> = {
  items: [{ ...trade, id: "trade-3", symbol: "TSLA" }], total: 3, next_cursor: null,
};

function SelectableTable({ onSelectionChange, onSelectedTradesChange }: {
  onSelectionChange: (ids: Set<string>) => void;
  onSelectedTradesChange: (trades: Trade[]) => void;
}) {
  const [selectedIds, setSelectedIds] = useState(new Set<string>());
  return <TradeTable selectedIds={selectedIds} onSelectedTradesChange={onSelectedTradesChange} onSelectionChange={(ids) => {
    setSelectedIds(ids);
    onSelectionChange(ids);
  }} />;
}

describe("TradeTable mobile controls", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    mockUseTrades.mockImplementation(({ cursor }: UseTradesOptions) => ({
      data: cursor === "cursor-2" ? lastPage : firstPage,
      isLoading: false, isError: false, isPlaceholderData: false, error: null, refetch: mockRefetch,
    }));
  });

  it.each([
    ["Opened: newest", "opened_at", "desc"],
    ["Opened: oldest", "opened_at", "asc"],
    ["Closed: newest", "closed_at", "desc"],
    ["Closed: oldest", "closed_at", "asc"],
    ["P&L: highest", "pnl", "desc"],
    ["P&L: lowest", "pnl", "asc"],
    ["Symbol: A → Z", "symbol", "asc"],
    ["Symbol: Z → A", "symbol", "desc"],
  ])("maps %s to the shared sort callback", async (label, sort_by, sort_dir) => {
    const user = userEvent.setup();
    const onSortChange = jest.fn();
    render(<TradeTable sort={{ sort_by: "closed_at", sort_dir: "desc" }} onSortChange={onSortChange} />);
    const select = screen.getByRole("combobox", { name: "Sort trades" });

    expect(within(select).getAllByRole("option")).toHaveLength(8);
    await user.selectOptions(select, within(select).getByRole("option", { name: label }));

    expect(onSortChange).toHaveBeenCalledWith({ sort_by, sort_dir });
  });

  it("reflects an externally supplied sort in the dropdown", () => {
    const { rerender } = render(<TradeTable sort={{ sort_by: "symbol", sort_dir: "asc" }} />);
    expect(screen.getByRole("combobox", { name: "Sort trades" })).toHaveValue("symbol:asc");

    rerender(<TradeTable sort={{ sort_by: "pnl", sort_dir: "desc" }} />);
    expect(screen.getByRole("combobox", { name: "Sort trades" })).toHaveValue("pnl:desc");
  });

  it("keeps card and desktop selection in sync and clears it when Done is pressed", async () => {
    const user = userEvent.setup();
    const onSelectionChange = jest.fn();
    const onSelectedTradesChange = jest.fn();
    render(<SelectableTable onSelectionChange={onSelectionChange} onSelectedTradesChange={onSelectedTradesChange} />);
    const cards = within(screen.getByTestId("trade-card-list"));
    const table = within(screen.getByRole("table"));

    expect(cards.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Select" }));
    expect(cards.getAllByRole("checkbox")).toHaveLength(2);
    await user.click(cards.getByRole("link", { name: "AAPL" }));

    expect(onSelectionChange).toHaveBeenLastCalledWith(new Set([trade.id]));
    expect(onSelectedTradesChange).toHaveBeenLastCalledWith([trade]);
    expect(cards.getByRole("checkbox", { name: "Select trade AAPL" })).toBeChecked();
    expect(table.getByRole("checkbox", { name: "Select trade AAPL" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Select all on page" })).toBePartiallyChecked();

    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(onSelectionChange).toHaveBeenLastCalledWith(new Set());
    expect(onSelectedTradesChange).toHaveBeenLastCalledWith([]);
    expect(cards.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(table.getByRole("checkbox", { name: "Select trade AAPL" })).not.toBeChecked();
    expect(screen.getByRole("combobox", { name: "Sort trades" })).toBeInTheDocument();
  });

  it("selects and deselects all trades on the current page from the mobile toolbar", async () => {
    const user = userEvent.setup();
    const onSelectionChange = jest.fn();
    const onSelectedTradesChange = jest.fn();
    render(<SelectableTable onSelectionChange={onSelectionChange} onSelectedTradesChange={onSelectedTradesChange} />);

    await user.click(screen.getByRole("button", { name: "Select" }));
    await user.click(screen.getByRole("checkbox", { name: "Select all on page" }));

    expect(onSelectionChange).toHaveBeenLastCalledWith(new Set(["trade-1", "trade-2"]));
    expect(onSelectedTradesChange).toHaveBeenLastCalledWith(firstPage.items);
    for (const checkbox of within(screen.getByTestId("trade-card-list")).getAllByRole("checkbox")) {
      expect(checkbox).toBeChecked();
    }
    await user.click(screen.getByRole("checkbox", { name: "Select all on page" }));
    expect(onSelectionChange).toHaveBeenLastCalledWith(new Set());
    expect(onSelectedTradesChange).toHaveBeenLastCalledWith([]);
  });

  it("pages forward and back with matching card/table data and correct boundary states", async () => {
    const user = userEvent.setup();
    render(<TradeTable />);

    expect(screen.getByRole("button", { name: "‹ Prev" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next ›" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Next ›" }));

    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: "cursor-2" }));
    expect(screen.getByRole("button", { name: "Next ›" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "‹ Prev" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next ›" }).parentElement).toHaveTextContent("Page 2");
    for (const variant of [within(screen.getByRole("table")), within(screen.getByTestId("trade-card-list"))]) {
      expect(variant.getByRole("link", { name: "TSLA" })).toBeInTheDocument();
      expect(variant.queryByRole("link", { name: "AAPL" })).not.toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "‹ Prev" }));
    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: undefined }));
    expect(within(screen.getByTestId("trade-card-list")).getAllByRole("link").map((link) => link.textContent)).toEqual(["AAPL", "MSFT"]);
    expect(screen.getByRole("button", { name: "‹ Prev" })).toBeDisabled();
  });

  it("resets mobile pagination when the sort changes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<TradeTable sort={{ sort_by: "opened_at", sort_dir: "desc" }} />);
    await user.click(screen.getByRole("button", { name: "Next ›" }));

    rerender(<TradeTable sort={{ sort_by: "pnl", sort_dir: "desc" }} />);

    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: undefined, sort: { sort_by: "pnl", sort_dir: "desc" } }));
    expect(screen.getByRole("button", { name: "‹ Prev" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next ›" }).parentElement).toHaveTextContent("Page 1");
  });

  it("preserves a nonstandard current page size and forwards mobile Rows changes", async () => {
    const user = userEvent.setup();
    const onLimitChange = jest.fn();
    render(<TradeTable limit={20} onLimitChange={onLimitChange} />);

    const rows = screen.getByRole("combobox", { name: "Rows" });
    expect(rows).toHaveValue("20");
    expect(within(rows).getAllByRole("option").map((option) => option.textContent)).toEqual(["20", "25", "50", "100"]);
    await user.selectOptions(rows, "50");
    expect(onLimitChange).toHaveBeenCalledWith(50);
  });

  it("renders the empty message independently in the desktop table and card list", () => {
    mockUseTrades.mockReturnValue({ data: { items: [], total: 0, next_cursor: null }, isLoading: false, isError: false });
    render(<TradeTable />);

    for (const variant of [within(screen.getByRole("table")), within(screen.getByTestId("trade-card-list"))]) {
      expect(variant.getByText("No trades found. Import trades to get started.")).toBeInTheDocument();
    }
  });

  it("shows one loading state instead of either list variant while fetching", () => {
    mockUseTrades.mockReturnValue({ isLoading: true, isError: false });
    render(<TradeTable portfolioId="portfolio-1" />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByTestId("trade-card-list")).not.toBeInTheDocument();
  });

  it("shows the request error and retries without rendering stale cards", async () => {
    const user = userEvent.setup();
    mockUseTrades.mockReturnValue({ isLoading: false, isError: true, error: new Error("Unavailable"), refetch: mockRefetch });
    render(<TradeTable portfolioId="portfolio-1" />);

    expect(screen.getByText("Failed to load trades.")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.queryByTestId("trade-card-list")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });
});
