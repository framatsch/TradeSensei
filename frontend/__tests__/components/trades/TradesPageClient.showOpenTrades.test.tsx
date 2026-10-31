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
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradesPageClient } from "@/app/dashboard/trades/TradesPageClient";
import type { UseTradesOptions } from "@/hooks/useTrades";
import type { Trade } from "@/lib/types";

const mockRouter = { push: jest.fn(), replace: jest.fn() };
let mockSearchParams = new URLSearchParams();
let mockSettingsLoading = false;
const mockUseTrades = jest.fn();
const mockShowOpenTrades = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockSearchParams,
}));

jest.mock("@/hooks/useShowOpenTrades", () => ({
  useShowOpenTrades: () => mockShowOpenTrades(),
}));

jest.mock("@/hooks/useSettings", () => ({
  useSettings: () => ({ data: { default_date_range: "all" }, isPlaceholderData: mockSettingsLoading }),
}));

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", isLoading: false }),
}));

jest.mock("@/hooks/useFeatureFlag", () => ({ __esModule: true, default: () => false }));
jest.mock("@/lib/api/index", () => ({}));

jest.mock("@/hooks/useSavedTradeFilters", () => ({
  useSavedTradeFilters: () => ({ data: [] }),
  useDeleteSavedTradeFilter: () => ({ mutate: jest.fn() }),
  useUpdateSavedTradeFilter: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useTrades", () => ({
  useTrades: (options: UseTradesOptions) => mockUseTrades(options),
  useBulkDeleteTrades: () => ({ mutate: jest.fn(), isPending: false }),
  useBulkAssignTaxonomy: () => ({ mutate: jest.fn(), isPending: false }),
  useBulkAssignPlaybook: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({ useGetTaxonomies: () => ({ data: [] }) }));
jest.mock("@/hooks/usePlaybooks", () => ({ usePlaybooks: () => ({ data: [] }) }));
jest.mock("@/hooks/useAccounts", () => ({ useAccounts: () => ({ data: [], isLoading: false }) }));
jest.mock("@/hooks/useAnnotationDefinitions", () => ({ useGetAnnotationDefinitions: () => ({ data: [] }) }));

jest.mock("@/components/trades/SaveFilterModal", () => ({
  SaveFilterModal: () => null,
}));

jest.mock("@/components/trades/MergePreviewModal", () => ({
  MergePreviewModal: () => null,
}));

const closedTrade: Trade = {
  id: "closed-trade",
  position_id: null,
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "10",
  entry_price: "100",
  exit_price: "110",
  stop_loss: null,
  take_profit: null,
  opened_at: "2026-10-24T12:00:00Z",
  closed_at: "2026-10-25T12:00:00Z",
  pnl: "100",
  net_pnl: "99",
  commission: "1",
  journal: null,
  user_rating: null,
  currency: "USD",
  pnl_eur: null,
  net_pnl_eur: null,
  tradingview_link: null,
  image_urls: [],
  playbook_id: null,
  playbook_name: null,
  account_id: "account-1",
  account_name: "IBKR Main",
  account_type: "ibkr",
  created_at: "2026-10-24T12:00:00Z",
  updated_at: "2026-10-25T12:00:00Z",
  is_manually_edited: false,
  tags: [],
  trade_notes: [],
};
const openTrade: Trade = { ...closedTrade, id: "open-trade", symbol: "TSLA", closed_at: null, exit_price: null, pnl: null, net_pnl: null };

describe("TradesPageClient show_open_trades behavior", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    mockSearchParams = new URLSearchParams();
    mockSettingsLoading = false;
    mockShowOpenTrades.mockReturnValue(false);
    mockUseTrades.mockImplementation(({ filters }: UseTradesOptions) => {
      const items = [closedTrade, openTrade].filter((trade) =>
        filters?.status === "closed" ? !!trade.closed_at : filters?.status === "open" ? !trade.closed_at : true,
      );
      return { data: { items, total: items.length, next_cursor: null }, isLoading: false, isError: false, isPlaceholderData: false };
    });
  });

  it("hides the status field in the desktop panel and mobile sheet when open trades are disabled", async () => {
    const user = userEvent.setup();
    render(<TradesPageClient />);

    await user.click(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name: "Filter" }));
    expect(within(screen.getByTestId("trade-desktop-filters")).queryByRole("combobox", { name: "Status" })).not.toBeInTheDocument();
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: "Filter" }));
    expect(within(screen.getByRole("dialog", { name: "Filters" })).queryByRole("combobox", { name: "Status" })).not.toBeInTheDocument();
  });

  it("shows the status field in both filter variants when open trades are enabled", async () => {
    const user = userEvent.setup();
    mockShowOpenTrades.mockReturnValue(true);
    render(<TradesPageClient />);

    await user.click(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name: "Filter" }));
    expect(within(screen.getByTestId("trade-desktop-filters")).getByRole("combobox", { name: "Status" })).toHaveValue("");
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: "Filter" }));
    expect(within(screen.getByRole("dialog", { name: "Filters" })).getByRole("combobox", { name: "Status" })).toHaveValue("");
  });

  it("explains and removes a stale open status while preserving the other URL filters", () => {
    mockSearchParams = new URLSearchParams("status=open&symbols=AAPL");
    render(<TradesPageClient />);

    expect(screen.getByText(/Open trades are currently hidden, and the status filter is forced to closed/)).toBeInTheDocument();
    expect(mockRouter.replace).toHaveBeenCalledWith("/dashboard/trades?symbols=AAPL", { scroll: false });
    fireEvent.click(screen.getByRole("button", { name: "Dismiss open-trades info banner" }));
    expect(screen.queryByText(/Open trades are currently hidden/)).not.toBeInTheDocument();
  });

  it("forces the list query to closed and renders only closed trades in both variants", () => {
    mockSearchParams = new URLSearchParams("status=open");
    render(<TradesPageClient />);

    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ filters: expect.objectContaining({ status: "closed" }) }));
    for (const variant of [within(screen.getByRole("table")), within(screen.getByTestId("trade-card-list"))]) {
      expect(variant.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/dashboard/trades/closed-trade");
      expect(variant.queryByRole("link", { name: "TSLA" })).not.toBeInTheDocument();
    }
  });

  it("does not enforce closed status or remove the URL while settings are placeholders", () => {
    mockSettingsLoading = true;
    mockSearchParams = new URLSearchParams("status=open");
    render(<TradesPageClient />);

    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ filters: expect.objectContaining({ status: "open" }) }));
    expect(mockRouter.replace).not.toHaveBeenCalled();
    expect(screen.queryByText(/Open trades are currently hidden/)).not.toBeInTheDocument();
  });

  it("honors an explicit open status in both trade variants when enabled", () => {
    mockShowOpenTrades.mockReturnValue(true);
    mockSearchParams = new URLSearchParams("status=open");
    render(<TradesPageClient />);

    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ filters: expect.objectContaining({ status: "open" }) }));
    for (const variant of [within(screen.getByRole("table")), within(screen.getByTestId("trade-card-list"))]) {
      expect(variant.getByRole("link", { name: "TSLA" })).toHaveAttribute("href", "/dashboard/trades/open-trade");
      expect(variant.queryByRole("link", { name: "AAPL" })).not.toBeInTheDocument();
    }
    expect(mockRouter.replace).not.toHaveBeenCalled();
  });

  it("renders the same ordered trades in the desktop table and mobile cards", () => {
    mockShowOpenTrades.mockReturnValue(true);
    render(<TradesPageClient />);

    for (const variant of [within(screen.getByRole("table")), within(screen.getByTestId("trade-card-list"))]) {
      expect(variant.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
        "/dashboard/trades/closed-trade",
        "/dashboard/trades/open-trade",
      ]);
    }
    expect(screen.getByRole("heading", { name: "Trades" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New Trade" })).toHaveAttribute("href", "/dashboard/trades/new");
  });

  it("updates the URL and effective query from the mobile sort select", async () => {
    const user = userEvent.setup();
    mockShowOpenTrades.mockReturnValue(true);
    mockSearchParams = new URLSearchParams("status=open&sort_by=symbol&sort_dir=asc&view_id=view-1");
    render(<TradesPageClient />);

    expect(screen.getByRole("combobox", { name: "Sort trades" })).toHaveValue("symbol:asc");
    await user.selectOptions(screen.getByRole("combobox", { name: "Sort trades" }), screen.getByRole("option", { name: "P&L: highest" }));

    expect(mockRouter.push).toHaveBeenCalledWith("/dashboard/trades?status=open&sort_by=pnl&sort_dir=desc&view_id=view-1", { scroll: false });
    expect(mockUseTrades).toHaveBeenLastCalledWith(expect.objectContaining({ sort: { sort_by: "pnl", sort_dir: "desc" }, filters: expect.objectContaining({ status: "open" }) }));
  });
});
