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
import { render, screen } from "@testing-library/react";
import { ExecutionRow } from "@/components/trades/ExecutionRow";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useUpdateExecution, useDeleteExecution, useRestoreExecution } from "@/hooks/useExecutions";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: jest.fn(() => ({ activePortfolioId: "portfolio-1" })),
}));

const mockMutateUpdate = jest.fn();
const mockMutateDelete = jest.fn();
const mockMutateRestore = jest.fn();

jest.mock("@/hooks/useExecutions", () => ({
  useUpdateExecution: () => ({ mutate: mockMutateUpdate, isPending: false }),
  useDeleteExecution: () => ({ mutate: mockMutateDelete, isPending: false }),
  useRestoreExecution: () => ({ mutate: mockMutateRestore, isPending: false }),
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
  id: "exec-1",
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
  created_at: "2024-01-01T12:00:00Z",
  updated_at: "2024-01-01T12:00:00Z",
};

describe("ExecutionRow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useActivePortfolio as jest.Mock).mockReturnValue({ activePortfolioId: "portfolio-1" });
  });

  it("shows lineage and allocated quantity markers for split child execution", () => {
    render(<table><tbody><ExecutionRow execution={splitExecution} trade={baseTrade} tradeId="trade-1" /></tbody></table>);

    expect(screen.getByText("Allocated")).toBeInTheDocument();
    expect(screen.getByText("↳ 0b18cd17")).toBeInTheDocument();
  });

  it("does not mutate when activePortfolioId is null", () => {
    (useActivePortfolio as jest.Mock).mockReturnValue({ activePortfolioId: null });
    render(<table><tbody><ExecutionRow execution={splitExecution} trade={baseTrade} tradeId="trade-1" /></tbody></table>);

    // For example, clicking delete and confirm
    const overflowButton = screen.getByRole("button", { name: "" }); // or find by icon
    // Wait, the action button depends on the state. It's better to just test that the functions like handleSave or handleRestore won't mutate.
    // Actually, it's easier to verify that the disabled state or early return works.
    // Let's just simulate a restore on a deleted row
    const deletedExecution = { ...splitExecution, deleted: true };
    render(<table><tbody><ExecutionRow execution={deletedExecution} trade={baseTrade} tradeId="trade-1" /></tbody></table>);
    
    // There is a Restore button
    const restoreBtn = screen.getByRole("button", { name: /restore/i });
    restoreBtn.click();
    
    // Should NOT have called mutate
    expect(mockMutateRestore).not.toHaveBeenCalled();
  });
});
