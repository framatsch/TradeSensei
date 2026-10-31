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
import { TradeMobileHeader } from "@/components/trades/TradeMobileHeader";
import type { Trade } from "@/lib/types";

const trade: Trade = {
  id: "trade-1",
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "100",
  entry_price: "182.40",
  exit_price: "186.52",
  stop_loss: "178",
  take_profit: null,
  opened_at: "2026-10-24T09:41:00Z",
  closed_at: "2026-10-25T15:12:00Z",
  pnl: "412.50",
  net_pnl: "412.50",
  commission: "1",
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
  created_at: "2026-10-24T09:41:00Z",
  updated_at: "2026-10-25T15:12:00Z",
  is_manually_edited: false,
  tags: [],
  position_id: null,
  user_rating: null,
  trade_notes: [],
};

function renderHeader(overrides: Partial<React.ComponentProps<typeof TradeMobileHeader>> = {}) {
  const props = {
    trade,
    realizedR: 1.8,
    returnPct: 2.3,
    holdingPeriod: "1d 5h",
    onCorrectTrade: jest.fn(),
    onMerge: jest.fn(),
    ...overrides,
  };
  return { ...render(<TradeMobileHeader {...props} />), props };
}

function getKpi(label: string) {
  const term = screen.getByText(label);
  return within(term.parentElement!).getByRole("definition");
}

describe("TradeMobileHeader", () => {
  it("renders the symbol, badges, holding period and positive KPI values", () => {
    renderHeader({ trade: { ...trade, is_manually_edited: true } });

    expect(screen.getByRole("heading", { name: "AAPL", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("LONG")).toBeInTheDocument();
    expect(screen.getByText("EQUITY")).toBeInTheDocument();
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("Manually Edited")).toBeInTheDocument();
    expect(screen.getByText(/Oct 24.*→.*Oct 25.*· 1d 5h/)).toBeInTheDocument();
    expect(getKpi("P&L")).toHaveTextContent("+$412.50");
    expect(getKpi("Realized R")).toHaveTextContent("+1.80R");
    expect(getKpi("Return %")).toHaveTextContent("+2.30%");
    expect(getKpi("P&L")).toHaveClass("text-success");
  });

  it("formats losing KPIs with a minus sign and the loss color", () => {
    renderHeader({ trade: { ...trade, pnl: "-88.40" }, realizedR: -0.5, returnPct: -2 });

    expect(getKpi("P&L")).toHaveTextContent("-$88.40");
    expect(getKpi("Realized R")).toHaveTextContent("-0.50R");
    expect(getKpi("Return %")).toHaveTextContent("-2.00%");
    for (const label of ["P&L", "Realized R", "Return %"]) {
      expect(getKpi(label)).toHaveClass("text-danger");
    }
  });

  it("renders zero KPIs as computed values rather than missing values", () => {
    renderHeader({ trade: { ...trade, pnl: "0" }, realizedR: 0, returnPct: 0 });

    expect(getKpi("P&L")).toHaveTextContent("+$0.00");
    expect(getKpi("Realized R")).toHaveTextContent("+0.00R");
    expect(getKpi("Return %")).toHaveTextContent("+0.00%");
  });

  it("renders a dash independently for every unavailable KPI", () => {
    renderHeader({ trade: { ...trade, pnl: null }, realizedR: null, returnPct: null });

    for (const label of ["P&L", "Realized R", "Return %"]) {
      expect(getKpi(label)).toHaveTextContent(/^—$/);
      expect(getKpi(label)).toHaveClass("text-muted-foreground");
    }
  });

  it("falls back only for Realized R when no stop loss is set", () => {
    renderHeader({ trade: { ...trade, stop_loss: null }, realizedR: null });

    expect(getKpi("Realized R")).toHaveTextContent(/^—$/);
    expect(getKpi("P&L")).toHaveTextContent("+$412.50");
    expect(getKpi("Return %")).toHaveTextContent("+2.30%");
  });

  it("renders an open trade as Ongoing without a manually edited badge", () => {
    renderHeader({ trade: { ...trade, closed_at: null }, holdingPeriod: "Ongoing" });

    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText(/→ — · Ongoing/)).toBeInTheDocument();
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
    expect(screen.queryByText("Manually Edited")).not.toBeInTheDocument();
  });

  it("hides direction for combo trades and renders COMBO instead of asset class", () => {
    renderHeader({ trade: { ...trade, is_combo: true, direction: "SHORT", asset_class: "OPTION" } });

    expect(screen.getByText("COMBO")).toBeInTheDocument();
    expect(screen.queryByText("SHORT")).not.toBeInTheDocument();
    expect(screen.queryByText("OPTION")).not.toBeInTheDocument();
  });

  it("discloses the corporate action when present", () => {
    renderHeader({
      trade: {
        ...trade,
        corporate_action_impact: [{
          id: "ca-1", symbol: "AAPL", date: "2026-10-24", ratio: "2", old_conid: null, new_conid: null,
        }],
      },
    });

    expect(screen.getByLabelText("Affected by a corporate action")).toHaveAttribute("title", "Split 2:1 on 2026-10-24");
  });

  it("omits the corporate action indicator when no actions apply", () => {
    renderHeader();

    expect(screen.queryByLabelText("Affected by a corporate action")).not.toBeInTheDocument();
  });

  it("uses the fallback Back to Trades URL", () => {
    renderHeader();

    expect(screen.getByRole("link", { name: "Back to Trades" })).toHaveAttribute("href", "/dashboard/trades");
  });

  it("renders supplied navigation and position slots and preserves the filtered back URL", () => {
    renderHeader({
      backHref: "/dashboard/trades?result=winners",
      navigationControls: <button>Next trade</button>,
      positionIndicator: <span>3 / 128</span>,
    });

    expect(screen.getByRole("link", { name: "Back to Trades" })).toHaveAttribute("href", "/dashboard/trades?result=winners");
    expect(screen.getByRole("button", { name: "Next trade" })).toBeInTheDocument();
    expect(screen.getByText("3 / 128")).toBeInTheDocument();
  });

  it.each([
    ["Correct Trade…", "onCorrectTrade"],
    ["Merge with…", "onMerge"],
  ] as const)("opens the actions menu and invokes %s", async (label, callback) => {
    const user = userEvent.setup();
    const { props } = renderHeader();
    const trigger = screen.getByRole("button", { name: "Trade actions" });
    trigger.focus();
    await user.keyboard("{Enter}");

    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: "Correct Trade…" })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "Merge with…" })).toBeInTheDocument();
    await user.click(within(menu).getByRole("menuitem", { name: label }));

    expect(props[callback]).toHaveBeenCalledTimes(1);
    expect(props[callback === "onMerge" ? "onCorrectTrade" : "onMerge"]).not.toHaveBeenCalled();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
