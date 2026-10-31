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
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExecutionLegsTable } from "@/components/trades/ExecutionLegsTable";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", activePortfolio: { id: "portfolio-1" }, portfolios: [] }),
}));

jest.mock("@/hooks/useExecutions", () => ({
  useTradeExecutions: jest.fn(),
  useReassignExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useDetachExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useUpdateExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useDeleteExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useRestoreExecution: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/components/trades/AddExecutionModal", () => ({
  AddExecutionModal: () => null,
}));

jest.mock("@/components/trades/TradePickerModal", () => ({
  TradePickerModal: () => null,
}));

jest.mock("@/components/trades/SplitExecutionModal", () => ({
  SplitExecutionModal: () => null,
}));

const { useTradeExecutions } = jest.requireMock("@/hooks/useExecutions") as {
  useTradeExecutions: jest.Mock;
};

const baseTrade: Trade = {
  id: "trade-1",
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "10",
  entry_price: "100",
  exit_price: null,
  stop_loss: null,
  take_profit: null,
  opened_at: "2024-01-01T00:00:00Z",
  closed_at: null,
  pnl: null,
  net_pnl: null,
  commission: "0",
  journal: null,
  currency: "USD",
  pnl_eur: null,
  net_pnl_eur: null,
  tradingview_link: null,
  image_urls: [],
  playbook_id: null,
  playbook_name: null,
  account_id: "account-1",
  account_name: "Main",
  account_type: "ibkr",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  is_manually_edited: false,
  tags: [],
  position_id: "pos-1",
  user_rating: 0,
  trade_notes: [],
};

const splitExecution: LogicalExecution = {
  id: "exec-split",
  trade_id: "trade-1",
  user_id: "user-1",
  account_id: "account-1",
  symbol: "AAPL",
  asset_class: "EQUITY",
  conid: null,
  direction: "LONG",
  quantity: "6",
  price: "100",
  raw_quantity: "6",
  raw_price: "100",
  commission: "0.6",
  pnl: null,
  pnl_eur: null,
  executed_at: "2024-01-01T12:00:00Z",
  origin: "split",
  deleted: false,
  user_modified: false,
  parent_id: "0b18cd17-51a6-4dc9-92d7-4c54a1a3e90a",
  currency: "USD",
  multiplier: 1,
  option_type: null,
  created_at: "2024-01-01T12:00:00Z",
  updated_at: "2024-01-01T12:00:00Z",
};

describe("ExecutionLegsTable", () => {
  beforeEach(() => {
    useTradeExecutions.mockReset();
  });

  it("renders split lineage markers when executions include parent_id", () => {
    useTradeExecutions.mockReturnValue({
      data: [splitExecution],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<ExecutionLegsTable tradeId="trade-1" trade={baseTrade} />);

    const table = within(screen.getByRole("table"));
    expect(screen.getByRole("heading", { name: "Execution Legs (1)" })).toBeInTheDocument();
    expect(table.getByText("Lineage")).toBeInTheDocument();
    expect(table.getByText("↳ 0b18cd17")).toBeInTheDocument();
    expect(table.getByText("Allocated")).toBeInTheDocument();
    expect(table.getByText("Split Child")).toBeInTheDocument();

    const cards = within(screen.getByTestId("execution-leg-card-list"));
    expect(cards.getByText("↳ 0b18cd17")).toBeInTheDocument();
    expect(cards.getByText("Allocated")).toBeInTheDocument();
    expect(cards.getByText("Split Child")).toBeInTheDocument();
  });

  it("renders Open/Close column and values for combo legs", () => {
    const comboTrade: Trade = {
      ...baseTrade,
      is_combo: true,
      symbol: "QQQ",
      asset_class: null,
      quantity: null,
      entry_price: null,
      position_id: null,
    };

    const legs: LogicalExecution[] = [
      {
        ...splitExecution,
        id: "leg-1",
        symbol: "QQQ 712C",
        asset_class: "OPTION",
        conid: "878467678",
        direction: "LONG",
        open_close: "O",
      },
      {
        ...splitExecution,
        id: "leg-2",
        symbol: "QQQ 722C",
        asset_class: "OPTION",
        conid: "884162799",
        direction: "SHORT",
        open_close: "C",
      },
    ];

    useTradeExecutions.mockReturnValue({
      data: legs,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<ExecutionLegsTable tradeId="trade-1" trade={comboTrade} />);

    const table = within(screen.getByRole("table"));
    expect(table.getByText("Open/Close")).toBeInTheDocument();
    expect(table.getByText("Open")).toBeInTheDocument();
    expect(table.getByText("Close")).toBeInTheDocument();
    expect(table.getByText("QQQ 712C")).toBeInTheDocument();
    expect(table.getByText("QQQ 722C")).toBeInTheDocument();

    const cards = within(screen.getByTestId("execution-leg-card-list")).getAllByRole("article");
    expect(within(cards[0]).getByText("QQQ 712C")).toBeInTheDocument();
    expect(within(cards[0]).getByText("Open")).toBeInTheDocument();
    expect(within(cards[1]).getByText("QQQ 722C")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Close")).toBeInTheDocument();
  });

  it("renders Strike, Type, Expiry columns when option legs are present", () => {
    const optionTrade: Trade = {
      ...baseTrade,
      is_combo: false,
    };

    const legs: LogicalExecution[] = [
      {
        ...splitExecution,
        id: "leg-1",
        symbol: "QQQ",
        asset_class: "OPTION",
        option_type: "C",
        strike: "712.00000000",
        expiry: "2025-10-03",
      }
    ];

    useTradeExecutions.mockReturnValue({
      data: legs,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<ExecutionLegsTable tradeId="trade-1" trade={optionTrade} />);

    const table = within(screen.getByRole("table"));
    expect(table.getByText("Strike")).toBeInTheDocument();
    expect(table.getByText("Type")).toBeInTheDocument();
    expect(table.getByText("Expiry")).toBeInTheDocument();
    expect(table.getByText("$712.00")).toBeInTheDocument();
    expect(table.getByText("Call")).toBeInTheDocument();
    expect(table.getByText(/Oct 3, 2025/)).toBeInTheDocument();

    const cards = within(screen.getByTestId("execution-leg-card-list"));
    expect(cards.getByText("$712.00")).toBeInTheDocument();
    expect(cards.getByText("Call")).toBeInTheDocument();
    expect(cards.getByText(/Oct 3, 2025/)).toBeInTheDocument();
  });

  it("renders a value-free corporate-action event row at the effective date", () => {
    const tradeWithCa = {
      ...baseTrade,
      chart_quantity: "10",
      corporate_action_impact: [
        {
          id: "ca-1",
          symbol: "AAPL",
          date: "2023-08-30",
          ratio: "0.25",
          old_conid: null,
          new_conid: null,
        }
      ]
    };
    useTradeExecutions.mockReturnValue({
      data: [splitExecution],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
    render(<ExecutionLegsTable tradeId="trade-1" trade={tradeWithCa} />);
    expect(screen.getByText(/Corporate Action: Split 1:4 on 2023-08-30/)).toBeInTheDocument();
  });

  it("renders the same ordered timeline as an expanded mobile card list and a desktop table", () => {
    const before = { ...splitExecution, id: "before", executed_at: "2024-01-01T12:00:00Z" };
    const after = { ...splitExecution, id: "after", direction: "SHORT" as const, executed_at: "2024-01-03T12:00:00Z" };
    useTradeExecutions.mockReturnValue({ data: [after, before], isLoading: false, isError: false });
    render(<ExecutionLegsTable tradeId="trade-1" trade={{
      ...baseTrade, chart_quantity: "10",
      corporate_action_impact: [{ id: "ca-1", symbol: "AAPL", date: "2024-01-02", ratio: "2", old_conid: null, new_conid: null }],
    }} />);

    expect(screen.getByRole("button", { name: "Execution Legs (2)" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("table")).toHaveClass("hidden", "lg:table");
    const list = screen.getByTestId("execution-leg-card-list");
    expect(list).toHaveClass("lg:hidden");
    expect(within(list).getAllByRole("article")).toHaveLength(2);
    expect(within(list.children[0] as HTMLElement).getByText("BUY")).toBeInTheDocument();
    expect(list.children[1]).toHaveTextContent("Split 2:1 on 2024-01-02");
    expect(list.children[1]).not.toHaveTextContent(/\$|@/);
    expect(within(list.children[2] as HTMLElement).getByText("SELL")).toBeInTheDocument();

    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[1]).toHaveTextContent("Corporate Action: Split 2:1 on 2024-01-02");
  });

  it("requests and displays deleted cards only when Show deleted is enabled", async () => {
    const user = userEvent.setup();
    const deleted = { ...splitExecution, id: "deleted", deleted: true };
    useTradeExecutions.mockImplementation((_tradeId, _portfolioId, includeDeleted) => ({
      data: includeDeleted ? [splitExecution, deleted] : [splitExecution], isLoading: false, isError: false,
    }));
    render(<ExecutionLegsTable tradeId="trade-1" trade={baseTrade} />);
    expect(within(screen.getByTestId("execution-leg-card-list")).getAllByRole("article")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Show deleted" }));

    expect(useTradeExecutions).toHaveBeenLastCalledWith("trade-1", "portfolio-1", true);
    const cards = within(screen.getByTestId("execution-leg-card-list"));
    expect(cards.getAllByRole("article")).toHaveLength(2);
    expect(cards.getByText("Deleted")).toBeInTheDocument();
    expect(cards.getByRole("button", { name: "Restore" })).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Execution Legs (1)" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Hide deleted (1)" }));
    expect(within(screen.getByTestId("execution-leg-card-list")).queryByText("Deleted")).not.toBeInTheDocument();
  });

  it("shows loading feedback without either execution representation", () => {
    useTradeExecutions.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    render(<ExecutionLegsTable tradeId="trade-1" trade={baseTrade} />);

    expect(screen.getByText("Loading executions…")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByTestId("execution-leg-card-list")).not.toBeInTheDocument();
  });

  it("lets the user retry a failed executions query", async () => {
    const user = userEvent.setup();
    const refetch = jest.fn();
    useTradeExecutions.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch });
    render(<ExecutionLegsTable tradeId="trade-1" trade={baseTrade} />);

    expect(screen.getByText(/Could not load executions/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
