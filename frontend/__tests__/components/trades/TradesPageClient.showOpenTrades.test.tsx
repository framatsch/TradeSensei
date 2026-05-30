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
import { TradesPageClient } from "@/app/dashboard/trades/TradesPageClient";

const mockPush = jest.fn();
const mockSearchParamsGet = jest.fn();

let capturedTradeFilterBarProps: any = null;
let capturedTradeTableProps: any = null;

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({
    get: (key: string) => mockSearchParamsGet(key),
    has: () => false,
    toString: () => "",
  }),
}));

jest.mock("@/hooks/useShowOpenTrades", () => ({
  useShowOpenTrades: jest.fn(),
}));

jest.mock("@/hooks/useSettings", () => ({
  useSettings: () => ({ data: { default_date_range: "all" } }),
}));

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1" }),
}));

jest.mock("@/hooks/useSavedTradeFilters", () => ({
  useSavedTradeFilters: () => ({ data: [] }),
  useDeleteSavedTradeFilter: () => ({ mutate: jest.fn() }),
  useUpdateSavedTradeFilter: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useTrades", () => ({
  useBulkDeleteTrades: () => ({ mutate: jest.fn(), isPending: false }),
  useBulkAssignTaxonomy: () => ({ mutate: jest.fn(), isPending: false }),
  useBulkAssignPlaybook: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({ useGetTaxonomies: () => ({ data: [] }) }));
jest.mock("@/hooks/usePlaybooks", () => ({ usePlaybooks: () => ({ data: [] }) }));

jest.mock("@/components/trades/BulkActionToolbar", () => ({
  BulkActionToolbar: () => <div data-testid="bulk-toolbar" />,
}));

jest.mock("@/components/trades/TradeFilterBar", () => ({
  TradeFilterBar: (props: any) => {
    capturedTradeFilterBarProps = props;
    return <div data-testid="trade-filter-bar" />;
  },
}));

jest.mock("@/components/trades/TradeTable", () => ({
  TradeTable: (props: any) => {
    capturedTradeTableProps = props;
    return <div data-testid="trade-table" />;
  },
}));

jest.mock("@/components/trades/SaveFilterModal", () => ({
  SaveFilterModal: () => null,
}));

jest.mock("@/components/trades/MergePreviewModal", () => ({
  MergePreviewModal: () => null,
}));

describe("TradesPageClient show_open_trades behavior", () => {
  const { useShowOpenTrades } = jest.requireMock("@/hooks/useShowOpenTrades") as {
    useShowOpenTrades: jest.Mock;
  };

  beforeEach(() => {
    jest.clearAllMocks();
    capturedTradeFilterBarProps = null;
    capturedTradeTableProps = null;
    mockSearchParamsGet.mockImplementation(() => null);
  });

  it("hides status filter toggle when show_open_trades is false", () => {
    useShowOpenTrades.mockReturnValue(false);

    render(<TradesPageClient />);

    expect(capturedTradeFilterBarProps.showOpenTrades).toBe(false);
  });

  it("shows status filter toggle when show_open_trades is true", () => {
    useShowOpenTrades.mockReturnValue(true);

    render(<TradesPageClient />);

    expect(capturedTradeFilterBarProps.showOpenTrades).toBe(true);
  });

  it("shows banner when show_open_trades is false and URL status=open", () => {
    useShowOpenTrades.mockReturnValue(false);
    mockSearchParamsGet.mockImplementation((key: string) => {
      if (key === "status") return "open";
      return null;
    });

    render(<TradesPageClient />);

    expect(
      screen.getByText(
        "Open trades are hidden. Enable 'Show Open Trades' in Settings → Features to show them."
      )
    ).toBeInTheDocument();
  });

  it("forces API status=closed when show_open_trades is false", () => {
    useShowOpenTrades.mockReturnValue(false);
    mockSearchParamsGet.mockImplementation((key: string) => {
      if (key === "status") return "open";
      return null;
    });

    render(<TradesPageClient />);

    expect(capturedTradeTableProps.filters.status).toBe("closed");
  });
});
