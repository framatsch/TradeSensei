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

import { ExecutionSummaryCard } from "@/components/trades/ExecutionSummaryCard";
import type { LogicalExecution, Trade } from "@/lib/types";

const comboTrade: Trade = {
  id: "trade-combo",
  symbol: "QQQ",
  direction: "LONG",
  asset_class: null,
  is_combo: true,
  multiplier: 1,
  quantity: null,
  entry_price: null,
  exit_price: null,
  stop_loss: null,
  take_profit: null,
  opened_at: "2026-07-07T14:17:18Z",
  closed_at: "2026-07-09T09:53:16Z",
  pnl: "77",
  net_pnl: "72",
  commission: "5",
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
  created_at: "2026-07-09T09:53:16Z",
  updated_at: "2026-07-09T09:53:16Z",
  is_manually_edited: false,
  tags: [],
  trade_notes: [],
  position_id: null,
};

function makeLeg(overrides: Partial<LogicalExecution>): LogicalExecution {
  return {
    id: "leg-id",
    trade_id: "trade-combo",
    user_id: "user-1",
    account_id: "account-1",
    symbol: "QQQ",
    asset_class: "OPTION",
    conid: "878467678",
    direction: "LONG",
    quantity: "1",
    price: "19.63",
    raw_quantity: "1",
    raw_price: "19.63",
    commission: "1.00",
    pnl: null,
    pnl_eur: null,
    executed_at: "2026-07-07T14:17:18Z",
    origin: "imported",
    deleted: false,
    user_modified: false,
    parent_id: null,
    currency: "USD",
    multiplier: 100,
    open_close: "O",
    created_at: "2026-07-07T14:17:18Z",
    updated_at: "2026-07-07T14:17:18Z",
    ...overrides,
  };
}

describe("ExecutionSummaryCard", () => {
  it("groups combo rows by conid and shows separate contract rows", () => {
    const legs: LogicalExecution[] = [
      makeLeg({ id: "l1", conid: "878467678", symbol: "QQQ 712C", direction: "LONG", open_close: "O" }),
      makeLeg({ id: "l2", conid: "884162799", symbol: "QQQ 722C", direction: "SHORT", open_close: "O", raw_price: "14.09", price: "14.09" }),
      makeLeg({ id: "l3", conid: "878467678", symbol: "QQQ 712C", direction: "SHORT", open_close: "C", pnl: "468", raw_price: "24.31", price: "24.31" }),
      makeLeg({ id: "l4", conid: "884162799", symbol: "QQQ 722C", direction: "LONG", open_close: "C", pnl: "-391", raw_price: "18", price: "18" }),
    ];

    render(<ExecutionSummaryCard trade={comboTrade} executions={legs} />);

    expect(screen.getByText("Execution Summary")).toBeInTheDocument();
    expect(screen.getByText(/QQQ 712C OPTION/)).toBeInTheDocument();
    expect(screen.getByText(/QQQ 722C OPTION/)).toBeInTheDocument();
    expect(screen.getByText("(878467678)")).toBeInTheDocument();
    expect(screen.getByText("(884162799)")).toBeInTheDocument();
  });


  it("renders a compact per-leg contract label for combo trades (no symbol/expiry repeated per row)", () => {
    // Strike/expiry are already sortable columns in the execution legs table
    // below, and the underlying symbol is already shown in the trade detail
    // page header — repeating "QQQ ... · Oct 3, 2025" on every combo row is
    // redundant, especially for multi-leg strategies (e.g. iron condors).
    const tradeWithOptions: Trade = {
      ...comboTrade,
      is_combo: true,
      symbol: "QQQ",
    };
    
    const optionLegs: LogicalExecution[] = [
      makeLeg({
        id: "leg-1",
        symbol: "QQQ",
        asset_class: "OPTION",
        option_type: "C",
        strike: "712",
        expiry: "2025-10-03",
        direction: "LONG",
        quantity: "1",
        price: "1.0",
        raw_quantity: "1",
        raw_price: "1.0",
      })
    ];

    render(<ExecutionSummaryCard trade={tradeWithOptions} executions={optionLegs} />);
    expect(screen.getByText("712 Call")).toBeInTheDocument();
    expect(screen.queryByText(/QQQ 712 Call/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Oct 3, 2025/)).not.toBeInTheDocument();
  });

  it("renders contract label subtitle for standard option trades", () => {
    const standardTrade: Trade = {
      ...comboTrade,
      is_combo: false,
      symbol: "QQQ",
    };
    
    const optionLegs: LogicalExecution[] = [
      makeLeg({
        id: "leg-1",
        symbol: "QQQ",
        asset_class: "OPTION",
        option_type: "C",
        strike: "712",
        expiry: "2025-10-03",
        direction: "LONG",
        quantity: "1",
        price: "1.0",
        raw_quantity: "1",
        raw_price: "1.0",
      })
    ];

    render(<ExecutionSummaryCard trade={standardTrade} executions={optionLegs} />);
    expect(screen.getByText(/QQQ 712 Call · Oct 3, 2025/)).toBeInTheDocument();
  });
});
