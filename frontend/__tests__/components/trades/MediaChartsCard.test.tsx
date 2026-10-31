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
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MediaChartsCard } from "@/components/trades/MediaChartsCard";
import type { Trade } from "@/lib/types";

jest.mock("@/hooks/useScreenshots", () => ({
  useUploadScreenshot: () => ({ mutate: jest.fn(), isPending: false }),
  useDeleteScreenshot: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useTrade", () => ({
  useUpdateTrade: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/components/charts/TradeChart", () => ({
  TradeChart: ({ trade }: { trade: Trade }) => (
    <div data-testid="mock-trade-chart">{trade.symbol}</div>
  ),
}));

const sampleTrade: Trade = {
  id: "trade-1",
  position_id: null,
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "100",
  entry_price: "180",
  exit_price: "190",
  stop_loss: "175",
  take_profit: "195",
  opened_at: "2026-10-24T09:41:00Z",
  closed_at: "2026-10-25T15:41:00Z",
  pnl: "1000",
  net_pnl: "998",
  commission: "2",
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
  account_name: "Main",
  account_type: "ibkr",
  created_at: "2026-10-24T09:41:00Z",
  updated_at: "2026-10-25T15:41:00Z",
  is_manually_edited: false,
  tags: [],
  taxonomies: [],
  trade_notes: [],
  annotations: [],
};

describe("MediaChartsCard", () => {
  beforeEach(() => {
    document.body.style.overflow = "";
  });

  it("maximizes the chart in-place on mobile and restores via Restore button or Escape", async () => {
    const user = userEvent.setup();
    render(<MediaChartsCard trade={sampleTrade} className="min-h-[360px]" />);

    const chartBefore = screen.getByTestId("mock-trade-chart");
    const maximizeBtn = screen.getByRole("button", { name: "Maximize chart" });
    expect(maximizeBtn).toHaveClass("lg:hidden");
    expect(screen.queryByRole("dialog", { name: "Maximized trade chart" })).not.toBeInTheDocument();

    await user.click(maximizeBtn);

    const dialog = screen.getByRole("dialog", { name: "Maximized trade chart" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveClass("fixed", "inset-0", "z-50", "w-screen", "h-[100dvh]");
    expect(document.body.style.overflow).toBe("hidden");
    // Same TradeChart DOM node stays mounted in-place
    expect(screen.getByTestId("mock-trade-chart")).toBe(chartBefore);

    const restoreBtn = screen.getByRole("button", { name: "Restore chart" });
    await user.click(restoreBtn);

    expect(screen.queryByRole("dialog", { name: "Maximized trade chart" })).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
    expect(screen.getByTestId("mock-trade-chart")).toBe(chartBefore);

    // Maximize again and close with Escape
    await user.click(screen.getByRole("button", { name: "Maximize chart" }));
    expect(screen.getByRole("dialog", { name: "Maximized trade chart" })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Maximized trade chart" })).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
  });

  it("hides the Maximize chart button and exits fullscreen when switching to Screenshots tab", async () => {
    const user = userEvent.setup();
    render(<MediaChartsCard trade={sampleTrade} />);

    await user.click(screen.getByRole("button", { name: "Maximize chart" }));
    expect(screen.getByRole("dialog", { name: "Maximized trade chart" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Screenshots/i }));

    expect(screen.queryByRole("dialog", { name: "Maximized trade chart" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Maximize chart|Restore chart/i })).not.toBeInTheDocument();
  });
});
