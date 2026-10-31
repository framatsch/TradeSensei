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
import { TradeCard } from "@/components/trades/TradeCard";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import type { Trade } from "@/lib/types";

const mockNavigate = jest.fn();
const mockAddNote = jest.fn();

jest.mock("next/link", () => ({
  __esModule: true,
  default: function MockLink({ href, onClick, ...props }: React.ComponentPropsWithoutRef<"a">) {
    return <a {...props} href={href} onClick={(event) => {
      onClick?.(event);
      if (!event.defaultPrevented) mockNavigate(href);
      event.preventDefault();
    }} />;
  },
}));

jest.mock("@/hooks/useFeatureFlag", () => ({ __esModule: true, default: jest.fn() }));
jest.mock("@/hooks/useNotes", () => ({
  useAddNote: () => ({ mutate: mockAddNote, isPending: false }),
}));

const trade: Trade = {
  id: "trade-1",
  position_id: null,
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "100",
  entry_price: "182.40",
  exit_price: "186.525",
  stop_loss: null,
  take_profit: null,
  opened_at: "2026-10-24T12:00:00Z",
  closed_at: "2026-10-25T12:00:00Z",
  pnl: "412.50",
  net_pnl: "410.50",
  commission: "2.00",
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
  is_manually_edited: false,
  created_at: "2026-10-24T12:00:00Z",
  updated_at: "2026-10-25T12:00:00Z",
  tags: [],
  trade_notes: [],
};

describe("TradeCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.mocked(useFeatureFlag).mockReturnValue(true);
  });

  it("renders trade values, taxonomy badges and the corporate-action indicator", () => {
    render(<TradeCard trade={{
      ...trade,
      taxonomies: [{ id: "tag-1", name: "Breakout", scope: "trades", color_hex: "#22c55e", is_archived: false, created_at: trade.created_at, updated_at: trade.updated_at }],
      corporate_action_impact: [{ id: "split-1", symbol: "AAPL", date: "2026-10-24", ratio: "2", old_conid: null, new_conid: null }],
    }} />);

    const card = within(screen.getByRole("article"));
    expect(card.getByRole("link", { name: "AAPL" })).toHaveAttribute("href", "/dashboard/trades/trade-1");
    expect(card.getByText("LONG")).toBeInTheDocument();
    expect(card.getByText("EQUITY")).toBeInTheDocument();
    expect(card.getByText("+$412.50")).toHaveClass("text-success");
    expect(card.getByText("100 @ $182.40 → $186.525")).toBeInTheDocument();
    expect(card.getByText("Oct 24 → Oct 25").parentElement).toHaveTextContent("IBKR Main");
    expect(card.getByText("Breakout")).toBeInTheDocument();
    expect(card.getByLabelText("Affected by a corporate action")).toHaveAttribute("title", "Split 2:1 on 2026-10-24");
    expect(card.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(card.queryByText("Open")).not.toBeInTheDocument();
  });

  it("shows open status and dash fallbacks for missing trade values", () => {
    render(<TradeCard trade={{ ...trade, direction: "SHORT", quantity: null, entry_price: null, exit_price: null, pnl: null, closed_at: null, account_name: null }} />);

    const card = within(screen.getByRole("article"));
    expect(card.getByText("Open")).toBeInTheDocument();
    expect(card.getByText("SHORT")).toBeInTheDocument();
    expect(card.getByText("— @ — → —")).toBeInTheDocument();
    expect(card.getByText("—", { exact: true })).toHaveClass("text-muted-foreground");
    expect(card.getByText("Oct 24 → —").parentElement).toHaveTextContent("Oct 24 → — · —");
    expect(card.queryByLabelText("Affected by a corporate action")).not.toBeInTheDocument();
  });

  it.each([
    ["-88.40", "-$88.40", "text-danger"],
    ["0", "+$0.00", "text-success"],
  ])("formats P&L %s with its sign and semantic color", (pnl, label, color) => {
    render(<TradeCard trade={{ ...trade, pnl }} />);
    expect(screen.getByText(label)).toHaveClass(color);
  });

  it.each(["pointer", "keyboard"])("opens the detail link using %s activation", async (activation) => {
    const user = userEvent.setup();
    render(<TradeCard trade={trade} />);
    const link = screen.getByRole("link", { name: "AAPL" });

    if (activation === "keyboard") {
      await user.tab();
      expect(link).toHaveFocus();
      await user.keyboard("{Enter}");
    } else {
      await user.click(link);
    }

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard/trades/trade-1");
  });

  it("hides direction and the underlying asset class for a combo trade", () => {
    render(<TradeCard trade={{ ...trade, is_combo: true, asset_class: "OPTION" }} />);

    expect(screen.getByText("COMBO")).toBeInTheDocument();
    expect(screen.queryByText("LONG")).not.toBeInTheDocument();
    expect(screen.queryByText("SHORT")).not.toBeInTheDocument();
    expect(screen.queryByText("OPTION")).not.toBeInTheDocument();
  });

  it.each([false, true])("toggles the notes input without navigation or selection (selection mode: %s)", async (selectionMode) => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    const tradeWithNotes: Trade = {
      ...trade,
      trade_notes: ["note-1", "note-2"].map((id) => ({ id, trade_id: trade.id, user_id: "user-1", content: "Observation", emotion: null, created_at: trade.created_at, updated_at: trade.updated_at })),
    };
    render(<TradeCard trade={tradeWithNotes} selectionMode={selectionMode} onSelect={onSelect} />);
    const notesButton = screen.getByRole("button", { name: "2 notes" });

    expect(notesButton).toHaveAttribute("aria-expanded", "false");
    await user.click(notesButton);
    expect(screen.getByPlaceholderText(/Live observation/)).toHaveFocus();
    expect(notesButton).toHaveAttribute("aria-expanded", "true");
    await user.click(notesButton);
    expect(screen.queryByPlaceholderText(/Live observation/)).not.toBeInTheDocument();
    await user.click(notesButton);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(notesButton).toHaveAttribute("aria-expanded", "false");
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("passes the card's trade ID to the quick-note mutation", async () => {
    const user = userEvent.setup();
    render(<TradeCard trade={trade} />);

    await user.click(screen.getByRole("button", { name: "Add note" }));
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    await user.type(screen.getByPlaceholderText(/Live observation/), "Waited for the retest");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mockAddNote).toHaveBeenCalledWith(
      { tradeId: trade.id, payload: { content: "Waited for the retest" } },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("omits note controls when quick notes are disabled", () => {
    jest.mocked(useFeatureFlag).mockReturnValue(false);
    render(<TradeCard trade={trade} />);

    expect(screen.queryByRole("button", { name: /note/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/Live observation/)).not.toBeInTheDocument();
  });

  it.each([false, true])("toggles card selection instead of navigating (selected: %s)", async (isSelected) => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(<TradeCard trade={trade} selectionMode isSelected={isSelected} onSelect={onSelect} />);
    expect(screen.getByRole("checkbox", { name: "Select trade AAPL" })).toHaveProperty("checked", isSelected);

    await user.click(screen.getByRole("link", { name: "AAPL" }));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(trade.id, !isSelected);
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("supports keyboard selection from the card link and checkbox", async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();
    render(<TradeCard trade={trade} selectionMode onSelect={onSelect} />);

    await user.tab();
    expect(screen.getByRole("checkbox", { name: "Select trade AAPL" })).toHaveFocus();
    await user.keyboard(" ");
    expect(onSelect).toHaveBeenCalledWith(trade.id, true);
    onSelect.mockClear();
    await user.tab();
    expect(screen.getByRole("link", { name: "AAPL" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(trade.id, true);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
