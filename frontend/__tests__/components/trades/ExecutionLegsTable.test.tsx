import React from "react";
import { render, screen } from "@testing-library/react";
import { ExecutionLegsTable } from "@/components/trades/ExecutionLegsTable";
import type { LogicalExecution, Trade } from "@/lib/types";

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
  notes: null,
  currency: "USD",
  pnl_eur: null,
  net_pnl_eur: null,
  tradingview_link: null,
  screenshots: [],
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
  direction: "LONG",
  quantity: "6",
  price: "100",
  commission: "0.6",
  pnl: null,
  executed_at: "2024-01-01T12:00:00Z",
  origin: "split",
  deleted: false,
  user_modified: false,
  parent_id: "0b18cd17-51a6-4dc9-92d7-4c54a1a3e90a",
  currency: "USD",
  multiplier: 1,
  created_at: "2024-01-01T12:00:00Z",
  updated_at: "2024-01-01T12:00:00Z",
};

describe("ExecutionLegsTable", () => {
  it("renders split lineage markers when executions include parent_id", () => {
    useTradeExecutions.mockReturnValue({
      data: [splitExecution],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<ExecutionLegsTable tradeId="trade-1" trade={baseTrade} />);

    expect(screen.getByText("Execution Legs")).toBeInTheDocument();
    expect(screen.getByText("Lineage")).toBeInTheDocument();
    expect(screen.getByText("↳ 0b18cd17")).toBeInTheDocument();
    expect(screen.getByText("Allocated")).toBeInTheDocument();
    expect(screen.getByText("Split Child")).toBeInTheDocument();
  });
});
