import React from "react";
import { render, screen } from "@testing-library/react";
import { TradeRow } from "@/components/trades/TradeRow";
import type { Trade } from "@/lib/types";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWithClient = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
};

const baseTrade = {
  id: "trade-1",
  position_id: null,
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
  opened_at: "2023-01-01T10:00:00Z",
  closed_at: null,
  pnl: null,
  net_pnl: null,
  commission: "1.00",
  account_id: "acct-1",
  account_name: "Test Account",
  tags: [],
  trade_notes: [],
  has_conflict: false,
  is_manually_edited: false
} as unknown as Trade;

describe("TradeRow", () => {
  it("renders a split indicator when corporate_action_impact is present", () => {
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
    renderWithClient(<table><tbody><TradeRow trade={tradeWithCa} /></tbody></table>);
    const indicator = screen.getByTitle(/Values may differ across the table/);
    expect(indicator).toBeInTheDocument();
    expect(indicator.getAttribute("title")).toContain("Split 1:4 on 2023-08-30");
    expect(indicator.getAttribute("title")).not.toMatch(/historical|original/i);
  });

  it("does not render a split indicator when corporate_action_impact is empty", () => {
    renderWithClient(<table><tbody><TradeRow trade={{ ...baseTrade, corporate_action_impact: [] }} /></tbody></table>);
    const indicator = screen.queryByTitle(/Values may differ/);
    expect(indicator).not.toBeInTheDocument();
  });
});
