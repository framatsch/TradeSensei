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
import { ExecutionLegCard } from "@/components/trades/ExecutionLegCard";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useDeleteExecution, useRestoreExecution, useUpdateExecution } from "@/hooks/useExecutions";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("@/hooks/useActivePortfolio", () => ({ useActivePortfolio: jest.fn() }));
jest.mock("@/hooks/useExecutions", () => ({
  useUpdateExecution: jest.fn(),
  useDeleteExecution: jest.fn(),
  useRestoreExecution: jest.fn(),
}));

const trade: Trade = {
  id: "trade-1",
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "100",
  entry_price: "182.40",
  exit_price: null,
  stop_loss: null,
  take_profit: null,
  opened_at: "2026-10-24T09:41:00Z",
  closed_at: null,
  pnl: null,
  net_pnl: null,
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
  updated_at: "2026-10-24T09:41:00Z",
  is_manually_edited: false,
  tags: [],
  position_id: null,
  user_rating: null,
  trade_notes: [],
};

const execution: LogicalExecution = {
  id: "exec-1",
  trade_id: "trade-1",
  user_id: "user-1",
  account_id: "account-1",
  symbol: "AAPL",
  asset_class: "EQUITY",
  conid: null,
  direction: "LONG",
  quantity: "100",
  price: "182.40",
  raw_quantity: "100",
  raw_price: "182.40",
  commission: "1",
  pnl: null,
  pnl_eur: null,
  executed_at: "2026-10-24T09:41:00Z",
  origin: "imported",
  deleted: false,
  user_modified: false,
  parent_id: null,
  source_id: "broker-1",
  currency: "USD",
  multiplier: 1,
  option_type: null,
  created_at: "2026-10-24T09:41:00Z",
  updated_at: "2026-10-24T09:41:00Z",
};

const updateExecution = jest.fn();
const deleteExecution = jest.fn();
const restoreExecution = jest.fn();

function renderCard(overrides: Partial<React.ComponentProps<typeof ExecutionLegCard>> = {}) {
  const props = {
    execution,
    trade,
    tradeId: trade.id,
    onMoveToTrade: jest.fn(),
    onDetach: jest.fn(),
    onSplit: jest.fn(),
    onLinkBroker: jest.fn(),
    ...overrides,
  };
  return { ...render(<ExecutionLegCard {...props} />), props };
}

async function openMenu(user: ReturnType<typeof userEvent.setup>) {
  screen.getByRole("button", { name: "Leg actions" }).focus();
  await user.keyboard("{Enter}");
  return within(screen.getByRole("menu"));
}

async function startEditing(user: ReturnType<typeof userEvent.setup>) {
  const menu = await openMenu(user);
  await user.click(menu.getByRole("menuitem", { name: "Edit" }));
  return within(screen.getByRole("form", { name: "Edit execution" }));
}

beforeEach(() => {
  jest.clearAllMocks();
  updateExecution.mockReset();
  deleteExecution.mockReset();
  restoreExecution.mockReset();
  (useActivePortfolio as jest.Mock).mockReturnValue({ activePortfolioId: "portfolio-1" });
  (useUpdateExecution as jest.Mock).mockReturnValue({ mutate: updateExecution, isPending: false });
  (useDeleteExecution as jest.Mock).mockReturnValue({ mutate: deleteExecution, isPending: false });
  (useRestoreExecution as jest.Mock).mockReturnValue({ mutate: restoreExecution, isPending: false });
});

describe("ExecutionLegCard read view", () => {
  it("renders side, as-traded amount, timestamp, commission, missing P&L and origin", () => {
    renderCard();

    const card = screen.getByRole("article");
    expect(within(card).getByText("BUY")).toHaveAttribute("title", "LONG");
    expect(card).toHaveTextContent("100 @ $182.40");
    expect(within(card).getByText(/Oct 24, 2026.*Comm\. \$1\.00/)).toBeInTheDocument();
    expect(card).toHaveTextContent("P&L —");
    expect(within(card).getByText("Imported")).toBeInTheDocument();
    expect(screen.queryByTitle(/split-adjusted/)).not.toBeInTheDocument();
    expect(screen.queryByText("Symbol")).not.toBeInTheDocument();
  });

  it("discloses adjusted values without replacing the as-traded values", () => {
    renderCard({ execution: { ...execution, quantity: "200", price: "91.20" } });

    expect(screen.getByRole("article")).toHaveTextContent(/100\s*\(200\) @ \$182\.40\s*\(\$91\.20\)/);
    expect(screen.getByTitle(/this value as 200 \(split-adjusted\)/)).toBeInTheDocument();
    expect(screen.getByTitle(/this value as \$91.20 \(split-adjusted\)/)).toBeInTheDocument();
  });

  it("renders split-child lineage and conflicting-leg feedback", () => {
    renderCard({
      execution: { ...execution, origin: "split", parent_id: "0b18cd17-51a6-4dc9-92d7-4c54a1a3e90a" },
      isConflict: true,
    });

    expect(screen.getByText("Split Child")).toBeInTheDocument();
    expect(screen.getByText("↳ 0b18cd17")).toHaveAttribute("title", "Parent execution: 0b18cd17-51a6-4dc9-92d7-4c54a1a3e90a");
    expect(screen.getByText("Allocated")).toBeInTheDocument();
    expect(screen.getByText("Conflict")).toBeInTheDocument();
    expect(screen.getByRole("article")).toHaveClass("border-l-warning");
  });

  it("shows combo-option contract fields and computes notional from raw values", () => {
    renderCard({
      trade: { ...trade, is_combo: true },
      execution: {
        ...execution, direction: "SHORT", symbol: "AAPL 261030P180", asset_class: "OPTION",
        open_close: "C", strike: "180", option_type: "P", expiry: "2026-10-30",
        raw_quantity: "2", quantity: "4", raw_price: "4.10", price: "2.05", multiplier: 100,
      },
    });

    expect(screen.getByText("SELL")).toBeInTheDocument();
    expect(screen.getByText("AAPL 261030P180")).toBeInTheDocument();
    expect(screen.getByText("OPTION")).toBeInTheDocument();
    expect(screen.getByText("Close")).toBeInTheDocument();
    expect(screen.getByText("$180.00")).toBeInTheDocument();
    expect(screen.getByText("Put")).toBeInTheDocument();
    expect(screen.getByText("Oct 30, 2026")).toBeInTheDocument();
    expect(screen.getByText(/Multiplier: 100 · Notional: \$820.00/)).toBeInTheDocument();
  });

  it.each([
    ["12.34", "+$12.34", "text-success"],
    ["-12.34", "-$12.34", "text-danger"],
    ["0", "+$0.00", "text-success"],
  ])("formats P&L %s with its sign and semantic color", (pnl, label, color) => {
    renderCard({ execution: { ...execution, pnl } });

    expect(screen.getByText(label)).toHaveClass(color);
  });
});

describe("ExecutionLegCard actions", () => {
  it.each([
    ["imported", "broker-1", true, false],
    ["manual", null, true, true],
    ["manual", "broker-1", true, false],
    ["split", null, false, false],
    ["merged", null, false, false],
  ] as const)("offers valid actions for %s with source %s", async (origin, sourceId, canSplit, canLinkBroker) => {
    const user = userEvent.setup();
    renderCard({ execution: { ...execution, origin, source_id: sourceId } });
    const menu = await openMenu(user);

    expect(menu.getByRole("menuitem", { name: "Edit" })).toBeInTheDocument();
    expect(menu.getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();
    expect(menu.getByRole("menuitem", { name: "Move to..." })).toBeInTheDocument();
    expect(menu.getByRole("menuitem", { name: "Detach as new Trade" })).toBeInTheDocument();
    expect(!!menu.queryByRole("menuitem", { name: "Split" })).toBe(canSplit);
    expect(!!menu.queryByRole("menuitem", { name: "Link broker transaction…" })).toBe(canLinkBroker);
  });

  it("hides optional actions when their callbacks are unavailable", async () => {
    const user = userEvent.setup();
    renderCard({ onSplit: undefined, onLinkBroker: undefined, onMoveToTrade: undefined, onDetach: undefined });
    const menu = await openMenu(user);

    expect(menu.getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Edit", "Delete"]);
  });

  it.each([
    ["Split", "onSplit", "execution"],
    ["Link broker transaction…", "onLinkBroker", "execution"],
    ["Move to...", "onMoveToTrade", "id"],
    ["Detach as new Trade", "onDetach", "id"],
  ] as const)("invokes %s with the selected execution", async (label, callback, argument) => {
    const user = userEvent.setup();
    const manual = { ...execution, origin: "manual" as const, source_id: null };
    const { props } = renderCard({ execution: manual });
    const menu = await openMenu(user);
    await user.click(menu.getByRole("menuitem", { name: label }));

    expect(props[callback]).toHaveBeenCalledTimes(1);
    expect(props[callback]).toHaveBeenCalledWith(argument === "id" ? manual.id : manual);
  });

  it("requires confirmation before deleting an execution", async () => {
    const user = userEvent.setup();
    deleteExecution.mockImplementation((_variables, options) => options.onSettled());
    renderCard();
    let menu = await openMenu(user);
    await user.click(menu.getByRole("menuitem", { name: "Delete" }));
    expect(screen.getByText(/Delete this execution\?/)).toBeInTheDocument();
    expect(deleteExecution).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText(/Delete this execution\?/)).not.toBeInTheDocument();
    expect(deleteExecution).not.toHaveBeenCalled();

    menu = await openMenu(user);
    await user.click(menu.getByRole("menuitem", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteExecution).toHaveBeenCalledWith(
      { executionId: "exec-1", tradeId: "trade-1", portfolioId: "portfolio-1" },
      expect.any(Object),
    );
    expect(screen.queryByText(/Delete this execution\?/)).not.toBeInTheDocument();
  });
});

describe("ExecutionLegCard editing", () => {
  it("edits raw values, saves the complete payload, and returns to read mode", async () => {
    const user = userEvent.setup();
    updateExecution.mockImplementation((_variables, options) => options.onSuccess());
    renderCard({ execution: { ...execution, quantity: "200", price: "91.20" } });
    const form = await startEditing(user);
    expect(form.getByRole("spinbutton", { name: "Quantity" })).toHaveValue(100);
    expect(form.getByRole("spinbutton", { name: "Price" })).toHaveValue(182.4);
    await user.click(form.getByRole("button", { name: "Set direction to SHORT" }));
    fireEvent.change(form.getByLabelText("Executed at date and time"), { target: { value: "2026-10-25T13:45" } });
    for (const [label, value] of [["Quantity", "50"], ["Price", "185.75"], ["Commission", "1.25"], ["P&L", "12.34"]]) {
      const input = form.getByRole("spinbutton", { name: label });
      await user.clear(input);
      await user.type(input, value);
    }
    expect(form.getByRole("button", { name: "Set direction to SHORT" })).toHaveAttribute("aria-pressed", "true");
    await user.click(form.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(updateExecution).toHaveBeenCalledWith({
      executionId: "exec-1", tradeId: "trade-1", portfolioId: "portfolio-1",
      data: {
        direction: "SHORT", executed_at: new Date("2026-10-25T13:45").toISOString(),
        quantity: "50", price: "185.75", commission: "1.25", pnl: "12.34",
      },
    }, expect.any(Object)));
    expect(screen.queryByRole("form", { name: "Edit execution" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Leg actions" })).toBeInTheDocument();
  });

  it("submits an empty optional P&L as null", async () => {
    const user = userEvent.setup();
    renderCard();
    const form = await startEditing(user);
    await user.click(form.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(updateExecution).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ pnl: null }) }), expect.any(Object),
    ));
  });

  it("discards edits on Cancel and reopens with the persisted values", async () => {
    const user = userEvent.setup();
    renderCard();
    let form = await startEditing(user);
    await user.clear(form.getByRole("spinbutton", { name: "Price" }));
    await user.type(form.getByRole("spinbutton", { name: "Price" }), "999");
    await user.click(form.getByRole("button", { name: "Cancel" }));
    expect(updateExecution).not.toHaveBeenCalled();

    form = await startEditing(user);
    expect(form.getByRole("spinbutton", { name: "Price" })).toHaveValue(182.4);
  });

  it.each([
    ["Quantity", "0", "Quantity must be greater than 0."],
    ["Price", "-1", "Price must not be negative."],
    ["Commission", "", "A number is required."],
  ])("rejects invalid %s without sending a mutation", async (label, value, message) => {
    const user = userEvent.setup();
    renderCard();
    const form = await startEditing(user);
    await user.clear(form.getByRole("spinbutton", { name: label }));
    if (value) await user.type(form.getByRole("spinbutton", { name: label }), value);
    await user.click(form.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(updateExecution).not.toHaveBeenCalled();
    expect(screen.getByRole("form", { name: "Edit execution" })).toBeInTheDocument();
  });

  it("keeps the draft and exposes the API error when saving fails", async () => {
    const user = userEvent.setup();
    updateExecution.mockImplementation((_variables, options) => options.onError({ detail: "Execution is locked." }));
    renderCard();
    const form = await startEditing(user);
    await user.clear(form.getByRole("spinbutton", { name: "Price" }));
    await user.type(form.getByRole("spinbutton", { name: "Price" }), "185");
    await user.click(form.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Execution is locked.");
    expect(form.getByRole("spinbutton", { name: "Price" })).toHaveValue(185);
  });

  it("disables form controls and announces the saving state while pending", async () => {
    const user = userEvent.setup();
    (useUpdateExecution as jest.Mock).mockReturnValue({ mutate: updateExecution, isPending: true });
    renderCard();
    const form = await startEditing(user);

    expect(screen.getByRole("form", { name: "Edit execution" })).toHaveAttribute("aria-busy", "true");
    expect(form.getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(form.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(form.getByRole("button", { name: "Set direction to SHORT" })).toBeDisabled();
    expect(form.getByRole("spinbutton", { name: "Price" })).toBeDisabled();
  });
});

describe("ExecutionLegCard restoring", () => {
  it("renders deleted legs with Restore instead of a menu and restores in the active portfolio", async () => {
    const user = userEvent.setup();
    const { rerender } = renderCard({ execution: { ...execution, deleted: true }, isConflict: true });
    expect(screen.getByRole("article")).toHaveClass("opacity-50");
    expect(screen.getByText("Deleted")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Leg actions" })).not.toBeInTheDocument();
    expect(screen.queryByText("Conflict")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Restore" }));

    expect(restoreExecution).toHaveBeenCalledWith(
      { executionId: "exec-1", tradeId: "trade-1", portfolioId: "portfolio-1" }, expect.any(Object),
    );
    rerender(<ExecutionLegCard execution={execution} trade={trade} tradeId={trade.id} />);
    expect(screen.getByRole("article")).not.toHaveClass("opacity-50");
    expect(screen.getByRole("button", { name: "Leg actions" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Restore" })).not.toBeInTheDocument();
  });

  it("reports a restore failure while keeping the deleted leg visible", async () => {
    const user = userEvent.setup();
    restoreExecution.mockImplementation((_variables, options) => options.onError({ detail: "Cannot restore execution." }));
    renderCard({ execution: { ...execution, deleted: true } });
    await user.click(screen.getByRole("button", { name: "Restore" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Cannot restore execution.");
    expect(screen.getByText("Deleted")).toBeInTheDocument();
  });

  it("disables Restore while the mutation is pending", () => {
    (useRestoreExecution as jest.Mock).mockReturnValue({ mutate: restoreExecution, isPending: true });
    renderCard({ execution: { ...execution, deleted: true } });

    expect(screen.getByRole("button", { name: "Restoring..." })).toBeDisabled();
  });

  it("does not restore without an active portfolio", async () => {
    const user = userEvent.setup();
    (useActivePortfolio as jest.Mock).mockReturnValue({ activePortfolioId: null });
    renderCard({ execution: { ...execution, deleted: true } });
    const restore = screen.getByRole("button", { name: "Restore" });
    expect(restore).toBeDisabled();
    await user.click(restore);

    expect(restoreExecution).not.toHaveBeenCalled();
  });
});
