import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortfolioSettings } from "@/components/settings/PortfolioSettings";
import { usePortfolios } from "@/hooks/usePortfolios";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { useAccounts } from "@/hooks/useAccounts";
import { PORTFOLIO_COLORS } from "@/lib/constants/portfolioColors";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as api from "@/lib/api/index";
import "@testing-library/jest-dom";

jest.mock("@/hooks/usePortfolios");
jest.mock("@/hooks/useSettings");
jest.mock("@/hooks/useAccounts");
jest.mock("@/lib/api/index");
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const mockUsePortfolios = usePortfolios as jest.Mock;
const mockUseSettings = useSettings as jest.Mock;
const mockUseUpdateSettings = useUpdateSettings as jest.Mock;
const mockUseAccounts = useAccounts as jest.Mock;

describe("PortfolioSettings", () => {
  let queryClient: QueryClient;
  let mockMutateAsync: jest.Mock;

  const mockPortfolios = [
    {
      id: "port-1",
      name: "Day Trading",
      base_currency: "USD",
      color_hex: PORTFOLIO_COLORS[0],
      has_trades: true,
    },
    {
      id: "port-2",
      name: "Long Term",
      base_currency: "EUR",
      color_hex: PORTFOLIO_COLORS[1],
      has_trades: false,
    },
  ];

  beforeEach(() => {
    queryClient = new QueryClient();
    mockMutateAsync = jest.fn().mockResolvedValue({});
    
    mockUsePortfolios.mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    mockUseSettings.mockReturnValue({
      data: {
        default_portfolio_id: "port-1",
      },
      isLoading: false,
    });

    mockUseUpdateSettings.mockReturnValue({
      mutate: mockMutateAsync,
      mutateAsync: mockMutateAsync,
    });

    mockUseAccounts.mockReturnValue({
      data: [],
      isLoading: false,
    });

    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <PortfolioSettings />
      </QueryClientProvider>
    );
  }

  it("renders portfolio list with colour chips and default indicator", () => {
    renderComponent();

    expect(screen.getByText("Day Trading")).toBeInTheDocument();
    expect(screen.getByText("Long Term")).toBeInTheDocument();

    const starButtons = screen.getAllByTitle("Set as default");
    expect(starButtons).toHaveLength(2);
    expect(starButtons[0].querySelector("svg")).toHaveClass("fill-[#eab308]");
    expect(starButtons[1].querySelector("svg")).not.toHaveClass("fill-[#eab308]");
  });

  it("create form submits with selected colour chip", async () => {
    (api.createPortfolioApiV1PortfoliosPost as jest.Mock).mockResolvedValue({});
    
    renderComponent();

    // Click create button
    fireEvent.click(screen.getByText("Create Portfolio"));

    // Fill name
    const nameInput = screen.getByPlaceholderText("e.g. Day Trading");
    fireEvent.change(nameInput, { target: { value: "New Port" } });

    // Select a color chip
    const colorChips = screen.getAllByRole("button").filter(b => b.style.backgroundColor);
    const targetColorIndex = 2;
    fireEvent.click(colorChips[targetColorIndex]);

    // Submit
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(api.createPortfolioApiV1PortfoliosPost).toHaveBeenCalledWith({
        body: {
          name: "New Port",
          base_currency: "USD",
          color_hex: PORTFOLIO_COLORS[targetColorIndex],
        }
      });
    });
  });

  it("delete confirmation blocks with 409 error message", async () => {
    (api.deletePortfolioApiV1PortfoliosPortfolioIdDelete as jest.Mock).mockRejectedValue({
      status: 409,
    });

    renderComponent();

    const deleteButtons = screen.getAllByRole("button").filter(b => b.innerHTML.includes("lucide-trash-2"));
    fireEvent.click(deleteButtons[0]);

    const confirmButton = await screen.findByText("Confirm Delete");
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Remove all accounts before deleting this portfolio");
    });
  });

  it("Set as default star click calls PUT /me/settings", async () => {
    renderComponent();

    const starButtons = screen.getAllByTitle("Set as default");
    fireEvent.click(starButtons[1]);

    expect(mockMutateAsync).toHaveBeenCalledWith({
      default_portfolio_id: "port-2",
    });
  });

  it("colour chip picker — only one chip active at a time; clicking new chip deselects previous", () => {
    renderComponent();

    fireEvent.click(screen.getByText("Create Portfolio"));

    const colorChips = screen.getAllByRole("button").filter(b => b.style.backgroundColor);
    
    expect(colorChips[0]).toHaveClass("ring-2");
    expect(colorChips[1]).not.toHaveClass("ring-2");

    fireEvent.click(colorChips[1]);

    expect(colorChips[0]).not.toHaveClass("ring-2");
    expect(colorChips[1]).toHaveClass("ring-2");
  });
});
