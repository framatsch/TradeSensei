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
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TradeDetailPage from "@/app/dashboard/trades/[id]/page";
import { useTrade } from "@/hooks/useTrade";
import { useBrokerTransactions, useTradeExecutions } from "@/hooks/useExecutions";
import { useTradeNavigation } from "@/hooks/useTradeNavigation";
import { useTrades } from "@/hooks/useTrades";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("next/navigation", () => ({ useParams: () => ({ id: "trade-1" }) }));
jest.mock("@/hooks/useTrade", () => ({
  useTrade: jest.fn(),
  useUpdateTrade: () => ({ mutate: jest.fn(), isPending: false }),
}));
jest.mock("@/hooks/useTradeNavigation", () => ({ useTradeNavigation: jest.fn() }));
jest.mock("@/hooks/useTrades", () => ({ useTrades: jest.fn() }));
jest.mock("@/hooks/useShowOpenTrades", () => ({ useShowOpenTrades: () => true }));
jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", activePortfolio: { id: "portfolio-1" } }),
}));
jest.mock("@/hooks/useFeatureFlag", () => () => false);

const mockMutate = jest.fn();
jest.mock("@/hooks/useExecutions", () => ({
  useTradeExecutions: jest.fn(),
  useBrokerTransactions: jest.fn(),
  useCreateExecution: () => ({ mutate: mockMutate, isPending: false }),
  useUpdateExecution: () => ({ mutate: mockMutate, isPending: false }),
  useDeleteExecution: () => ({ mutate: mockMutate, isPending: false }),
  useRestoreExecution: () => ({ mutate: mockMutate, isPending: false }),
  useReassignExecution: () => ({ mutate: mockMutate, isPending: false }),
  useDetachExecution: () => ({ mutate: mockMutate, isPending: false }),
  useSplitExecution: () => ({ mutate: mockMutate, isPending: false }),
  useLinkBrokerTransaction: () => ({ mutate: mockMutate, isPending: false }),
}));

// Keep the real ExecutionLegsTable, rows/cards, editor, and all execution dialogs.
// Only unrelated sections and data hooks are replaced; no query provider or HTTP.
jest.mock("@/components/trades/MediaChartsCard", () => ({ MediaChartsCard: () => null }));
jest.mock("@/components/trades/ExecutionSummaryCard", () => ({ ExecutionSummaryCard: () => null }));
jest.mock("@/components/trades/QualitativeMetadataPanel", () => ({ QualitativeMetadataPanel: () => null }));
jest.mock("@/components/notes/NoteList", () => ({ NoteList: () => null }));

const trade: Trade = {
  id: "trade-1",
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "10",
  chart_quantity: "10",
  entry_price: "100",
  exit_price: null,
  stop_loss: null,
  take_profit: null,
  opened_at: "2026-10-24T09:41:00Z",
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
  created_at: "2026-10-24T09:41:00Z",
  updated_at: "2026-10-24T09:41:00Z",
  is_manually_edited: false,
  tags: [],
  position_id: null,
  user_rating: null,
  trade_notes: [],
};

const execution: LogicalExecution = {
  id: "exec-1",
  trade_id: trade.id,
  user_id: "user-1",
  account_id: "account-1",
  symbol: trade.symbol,
  asset_class: "EQUITY",
  conid: null,
  direction: "LONG",
  quantity: "10",
  price: "100",
  raw_quantity: "10",
  raw_price: "100",
  commission: "0",
  pnl: null,
  pnl_eur: null,
  executed_at: trade.opened_at,
  origin: "manual",
  deleted: false,
  user_modified: false,
  parent_id: null,
  source_id: null,
  currency: "USD",
  multiplier: 1,
  option_type: null,
  created_at: trade.created_at,
  updated_at: trade.updated_at,
};

const navigation = {
  available: true,
  prevId: "trade-0",
  nextId: "trade-2",
  canGoPrev: true,
  canGoNext: true,
  prevSymbol: "MSFT",
  nextSymbol: "TSLA",
  position: 2,
  total: 3,
  sourceLabel: "All trades",
  isLoadingNext: false,
  navigationError: null,
  goPrev: jest.fn(),
  goNext: jest.fn().mockResolvedValue(undefined),
  backHref: "/dashboard/trades",
};

const legDialogs = [
  { action: "Split", name: "Split Execution", confirm: "Confirm Split" },
  { action: "Link broker transaction…", name: "Link broker transaction", confirm: "Link transaction" },
  { action: "Move to...", name: "Select Trade", confirm: "Move Here" },
  { action: "Detach as new Trade", name: "Detach Execution", confirm: "Detach" },
] as const;

beforeEach(() => {
  jest.clearAllMocks();
  (useTrade as jest.Mock).mockReturnValue({ data: trade, isLoading: false, isError: false });
  (useTradeExecutions as jest.Mock).mockReturnValue({ data: [execution], isLoading: false, isError: false });
  (useBrokerTransactions as jest.Mock).mockReturnValue({ data: [], isLoading: false, isError: false });
  (useTrades as jest.Mock).mockReturnValue({ data: { items: [], next_cursor: null, total: 0 }, isLoading: false });
  (useTradeNavigation as jest.Mock).mockReturnValue(navigation);
});

async function showExecutions(user: ReturnType<typeof userEvent.setup>) {
  render(<TradeDetailPage />);
  await user.click(screen.getByRole("tab", { name: "Executions (1)" }));
  return within(screen.getByRole("tabpanel", { name: "Executions (1)" }));
}

async function expectDialogBlocksTradeArrows(
  user: ReturnType<typeof userEvent.setup>, name: string, confirmLabel: string,
) {
  // Wait for the initiating Radix menu to unmount: it must not mask missing
  // semantics on the actual dialog. Dispatch outside inputs so only the global
  // dialog guard, not the editable-target guard, can stop trade navigation.
  await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
  const dialog = screen.getByRole("dialog", { name });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(within(dialog).getByRole("heading", { name })).toBeInTheDocument();
  expect(within(dialog).getByRole("button", { name: confirmLabel })).toBeInTheDocument();
  for (const key of ["ArrowLeft", "ArrowRight"]) {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    fireEvent(document.body, event);
    expect(event.defaultPrevented).toBe(false);
  }
  expect(navigation.goPrev).not.toHaveBeenCalled();
  expect(navigation.goNext).not.toHaveBeenCalled();

  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.keyDown(document.body, { key: "ArrowLeft" });
  fireEvent.keyDown(document.body, { key: "ArrowRight" });
  expect(navigation.goPrev).toHaveBeenCalledTimes(1);
  expect(navigation.goNext).toHaveBeenCalledTimes(1);
  expect(mockMutate).not.toHaveBeenCalled();
}

describe("TradeDetailPage actual execution dialog keyboard guards", () => {
  it("blocks both arrows for the real Add Execution dialog opened from the execution table", async () => {
    const user = userEvent.setup();
    const executions = await showExecutions(user);
    await user.click(executions.getByRole("button", { name: "Add Execution" }));

    await expectDialogBlocksTradeArrows(user, "Add Execution", "Add Execution");
  });

  describe.each(["mobile card", "desktop row"] as const)("%s actions", (surface) => {
    it.each(legDialogs)("blocks both arrows for the actual $name dialog", async ({ action, name, confirm }) => {
      const user = userEvent.setup();
      const executions = await showExecutions(user);
      const container = surface === "mobile card"
        ? executions.getByTestId("execution-leg-card-list")
        : executions.getByRole("table");
      const triggerLabel = surface === "mobile card" ? "Leg actions" : "Row actions";
      within(container).getByRole("button", { name: triggerLabel }).focus();
      await user.keyboard("{Enter}");
      await user.click(screen.getByRole("menuitem", { name: action }));

      await expectDialogBlocksTradeArrows(user, name, confirm);
    });
  });
});
