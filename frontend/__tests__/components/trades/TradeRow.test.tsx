import React from "react";
import { render, screen, within } from "@testing-library/react";
import { TradeRow } from "@/components/trades/TradeRow";
import { TradeCard } from "@/components/trades/TradeCard";
import type { Trade } from "@/lib/types";

jest.mock("@/hooks/useFeatureFlag", () => ({ __esModule: true, default: () => false }));
jest.mock("@/hooks/useNotes", () => ({ useAddNote: jest.fn() }));

const renderTradeVariants = (trade: Trade) => {
  render(
    <>
      <table><tbody><TradeRow trade={trade} /></tbody></table>
      <div data-testid="trade-card-list"><TradeCard trade={trade} /></div>
    </>
  );
  return within(screen.getByRole("table"));
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
    const table = renderTradeVariants(tradeWithCa);
    const indicator = table.getByLabelText("Affected by a corporate action");
    expect(indicator).toBeInTheDocument();
    expect(indicator.getAttribute("title")).toContain("Split 1:4 on 2023-08-30");
    expect(indicator.getAttribute("title")).not.toMatch(/historical|original/i);
    expect(within(screen.getByTestId("trade-card-list")).getByLabelText("Affected by a corporate action")).toHaveAttribute("title", "Split 1:4 on 2023-08-30");
  });

  it("does not render a split indicator when corporate_action_impact is empty", () => {
    const table = renderTradeVariants({ ...baseTrade, corporate_action_impact: [] });
    const indicator = table.queryByLabelText("Affected by a corporate action");
    expect(indicator).not.toBeInTheDocument();
    expect(within(screen.getByTestId("trade-card-list")).queryByLabelText("Affected by a corporate action")).not.toBeInTheDocument();
  });

  it("keeps desktop and mobile symbol links and combo badges consistent", () => {
    const table = renderTradeVariants({ ...baseTrade, is_combo: true, asset_class: "OPTION" });
    const cards = within(screen.getByTestId("trade-card-list"));

    for (const variant of [table, cards]) {
      expect(variant.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/dashboard/trades/trade-1");
      expect(variant.getByText("COMBO")).toBeInTheDocument();
      expect(variant.queryByText("LONG")).not.toBeInTheDocument();
      expect(variant.queryByText("OPTION")).not.toBeInTheDocument();
    }
  });
});
