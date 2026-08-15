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
import TradeDetailPage from "@/app/dashboard/trades/[id]/page";
import { useTrade } from "@/hooks/useTrade";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "trade-1" }),
}));

jest.mock("@/hooks/useTrade", () => ({
  useTrade: jest.fn(),
  useUpdateTrade: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useExecutions", () => ({
  useTradeExecutions: () => ({ data: [], isLoading: false }),
}));

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolio: { id: "portfolio-1" } }),
}));

jest.mock("@/hooks/useFeatureFlag", () => jest.fn(() => false));

// Mock child components to isolate the test
jest.mock("@/components/trades/MediaChartsCard", () => ({
  MediaChartsCard: () => <div data-testid="media-charts-card" />
}));
jest.mock("@/components/trades/ExecutionSummaryCard", () => ({
  ExecutionSummaryCard: () => <div data-testid="execution-summary-card" />
}));
jest.mock("@/components/trades/ExecutionLegsTable", () => ({
  ExecutionLegsTable: () => <div data-testid="execution-legs-table" />
}));
jest.mock("@/components/notes/NoteList", () => ({
  NoteList: () => <div data-testid="note-list" />
}));
jest.mock("@/components/trades/QualitativeMetadataPanel", () => ({
  QualitativeMetadataPanel: () => <div data-testid="qualitative-metadata-panel" />
}));
jest.mock("lucide-react", () => ({
  ...jest.requireActual("lucide-react"),
  Split: () => <svg data-testid="split-icon" />
}));

const baseTrade = {
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
  opened_at: "2024-01-01T00:00:00Z",
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
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  is_manually_edited: false,
  tags: [],
  position_id: null,
  user_rating: 0,
  trade_notes: [],
  has_conflict: false,
  has_unlinked_executions: false,
};

describe("TradeDetailPage Corporate Action Indicator", () => {
  it("renders the corporate action indicator when corporate_action_impact is present", () => {
    (useTrade as jest.Mock).mockReturnValue({
      data: {
        ...baseTrade,
        corporate_action_impact: [
          {
            id: "ca-1",
            symbol: "AAPL",
            date: "2024-02-01",
            ratio: "0.25",
            old_conid: null,
            new_conid: null,
          }
        ]
      },
      isLoading: false,
      isError: false,
    });

    render(<TradeDetailPage />);

    expect(screen.getByLabelText(/Affected by a corporate action/i)).toBeInTheDocument();
  });

  it("does not render the corporate action indicator when corporate_action_impact is empty", () => {
    (useTrade as jest.Mock).mockReturnValue({
      data: {
        ...baseTrade,
        corporate_action_impact: []
      },
      isLoading: false,
      isError: false,
    });

    render(<TradeDetailPage />);

    expect(screen.queryByLabelText(/Affected by a corporate action/i)).not.toBeInTheDocument();
  });

  it("renders unlinked execution notice when has_unlinked_executions is true", () => {
    (useTrade as jest.Mock).mockReturnValue({
      data: {
        ...baseTrade,
        has_unlinked_executions: true,
        corporate_action_impact: [],
      },
      isLoading: false,
      isError: false,
    });

    render(<TradeDetailPage />);

    expect(screen.getByText(/protected trade has unlinked executions from import/i)).toBeInTheDocument();
  });

  it("hides unlinked execution notice when has_unlinked_executions is false", () => {
    (useTrade as jest.Mock).mockReturnValue({
      data: {
        ...baseTrade,
        has_unlinked_executions: false,
        corporate_action_impact: [],
      },
      isLoading: false,
      isError: false,
    });

    render(<TradeDetailPage />);

    expect(screen.queryByText(/protected trade has unlinked executions from import/i)).not.toBeInTheDocument();
  });
});
