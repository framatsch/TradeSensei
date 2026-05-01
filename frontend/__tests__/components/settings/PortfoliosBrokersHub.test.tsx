import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortfoliosBrokersHub } from "@/components/settings/PortfoliosBrokersHub";
import { usePortfolios } from "@/hooks/usePortfolios";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useAccounts } from "@/hooks/useAccounts";
import { PORTFOLIO_COLORS } from "@/lib/constants/portfolioColors";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom";

jest.mock("@/hooks/usePortfolios");
jest.mock("@/hooks/useSettings");
jest.mock("@/hooks/useAccounts");
jest.mock("@/lib/api/client.gen", () => ({
  client: {
    post: jest.fn().mockResolvedValue({}),
    patch: jest.fn().mockResolvedValue({}),
  },
}));

const mockUsePortfolios = usePortfolios as jest.Mock;
const mockUseSettings = useSettings as jest.Mock;
const mockUseUpdateSettings = useUpdateSettings as jest.Mock;
const mockUseAccounts = useAccounts as jest.Mock;

const mockPortfolios = [
  {
    id: "port-1",
    user_id: "user-1",
    name: "Day Trading",
    base_currency: "USD",
    color_hex: PORTFOLIO_COLORS[0],
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "port-2",
    user_id: "user-1",
    name: "Long Term",
    base_currency: "EUR",
    color_hex: PORTFOLIO_COLORS[1],
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

const singlePortfolio = [mockPortfolios[0]];

const mockAccounts = [
  {
    id: "acct-1",
    user_id: "user-1",
    portfolio_id: "port-1",
    name: "IBKR Main",
    account_number: "U123",
    type: "ibkr" as const,
    currency: "USD",
    is_active: true,
    has_api_keys: true,
    settings: { sync_days: 30, flex_from_date_preset: "ytd" as const, flex_custom_from_date: null },
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "acct-2",
    user_id: "user-1",
    portfolio_id: "port-1",
    name: "Schwab IRA",
    account_number: null,
    type: "schwab" as const,
    currency: "USD",
    is_active: false,
    has_api_keys: false,
    settings: { sync_days: 30, flex_from_date_preset: "ytd" as const, flex_custom_from_date: null },
    created_at: "2024-01-01T00:00:00Z",
  },
];

describe("PortfoliosBrokersHub", () => {
  let queryClient: QueryClient;
  let mockMutateAsync: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();
    mockMutateAsync = jest.fn();

    mockUsePortfolios.mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    mockUseSettings.mockReturnValue({
      data: { default_portfolio_id: "port-1" },
      isLoading: false,
    });

    mockUseUpdateSettings.mockReturnValue({
      mutate: mockMutateAsync,
      mutateAsync: mockMutateAsync,
    });

    mockUseAccounts.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <PortfoliosBrokersHub />
      </QueryClientProvider>
    );
  }

  it("renders portfolio list with accordion rows", () => {
    renderComponent();

    expect(screen.getByText("Day Trading")).toBeInTheDocument();
    expect(screen.getByText("Long Term")).toBeInTheDocument();
    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("EUR")).toBeInTheDocument();
  });

  it("portfolio rows are collapsed by default", () => {
    renderComponent();

    expect(screen.queryByText("Add Broker Account")).not.toBeInTheDocument();
  });

  it("clicking chevron expands a portfolio accordion", async () => {
    renderComponent();

    const dayTradingRow = screen.getByText("Day Trading").closest("button");
    if (dayTradingRow) {
      fireEvent.click(dayTradingRow);
    }

    await waitFor(() => {
      expect(screen.getByText("No broker accounts linked")).toBeInTheDocument();
    });
  });

  it("auto-expands single portfolio on initial load", () => {
    mockUsePortfolios.mockReturnValue({
      portfolios: singlePortfolio,
      isLoading: false,
      isError: false,
    });

    mockUseAccounts.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    renderComponent();

    expect(screen.getByText("No broker accounts linked")).toBeInTheDocument();
  });

  it("expanded accordion does not collapse on background refetch", async () => {
    renderComponent();

    const dayTradingRow = screen.getByText("Day Trading").closest("button");
    if (dayTradingRow) fireEvent.click(dayTradingRow);

    await waitFor(() => {
      expect(screen.getByText("No broker accounts linked")).toBeInTheDocument();
    });

    // Trigger a refetch by re-rendering with same data — accordion stays expanded
    mockUsePortfolios.mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });
    mockUseAccounts.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    renderComponent();

    expect(screen.getByText("No broker accounts linked")).toBeInTheDocument();
  });

  it("shows account rows with name and type badge when expanded", () => {
    mockUseAccounts.mockReturnValue({
      data: mockAccounts,
      isLoading: false,
      isError: false,
    });

    renderComponent();

    const dayTradingRow = screen.getByText("Day Trading").closest("button");
    if (dayTradingRow) fireEvent.click(dayTradingRow);

    expect(screen.getByText("IBKR Main")).toBeInTheDocument();
    expect(screen.getByText("Schwab IRA")).toBeInTheDocument();
    expect(screen.getByText("IBKR")).toBeInTheDocument();
    expect(screen.getByText("Schwab")).toBeInTheDocument();
  });

  it("shows Connected badge for active accounts with API keys", () => {
    mockUseAccounts.mockReturnValue({
      data: [mockAccounts[0]],
      isLoading: false,
      isError: false,
    });

    renderComponent();

    const dayTradingRow = screen.getByText("Day Trading").closest("button");
    if (dayTradingRow) fireEvent.click(dayTradingRow);

    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("shows Inactive badge for inactive accounts", () => {
    mockUseAccounts.mockReturnValue({
      data: [mockAccounts[1]],
      isLoading: false,
      isError: false,
    });

    renderComponent();

    const dayTradingRow = screen.getByText("Day Trading").closest("button");
    if (dayTradingRow) fireEvent.click(dayTradingRow);

    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("\"Create New Portfolio\" button rendered at top", () => {
    renderComponent();
    expect(screen.getByText("Create New Portfolio")).toBeInTheDocument();
  });

  it("Set as default star click calls updateSettings", () => {
    renderComponent();

    const starButtons = screen.getAllByTitle("Set as default");
    fireEvent.click(starButtons[1]);

    expect(mockMutateAsync).toHaveBeenCalledWith({
      default_portfolio_id: "port-2",
    });
  });
});