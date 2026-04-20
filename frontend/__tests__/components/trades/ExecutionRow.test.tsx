import React from "react";
import { render, screen } from "@testing-library/react";
import { ExecutionRow } from "@/components/trades/ExecutionRow";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("@/hooks/useExecutions", () => ({
  useUpdateExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useDeleteExecution: () => ({ mutate: jest.fn(), isPending: false }),
  useRestoreExecution: () => ({ mutate: jest.fn(), isPending: false }),
}));

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
  trade_notes: [],
};

const splitExecution: LogicalExecution = {
  id: "exec-1",
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

describe("ExecutionRow", () => {
  it("shows lineage and allocated quantity markers for split child execution", () => {
    render(<table><tbody><ExecutionRow execution={splitExecution} trade={baseTrade} tradeId="trade-1" /></tbody></table>);

    expect(screen.getByText("Allocated")).toBeInTheDocument();
    expect(screen.getByText("↳ 0b18cd17")).toBeInTheDocument();
  });
});
