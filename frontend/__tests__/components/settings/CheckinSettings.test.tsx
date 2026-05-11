import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom";

import { CheckinSettings } from "@/components/settings/CheckinSettings";
import {
  useCreateMarketIndex,
  useDeleteMarketIndex,
  useMarketIndexes,
  useUpdateMarketIndex,
} from "@/hooks/useCheckinDefinitions";

jest.mock("@/hooks/useCheckinDefinitions");

const mockUseMarketIndexes = useMarketIndexes as jest.Mock;
const mockUseCreateMarketIndex = useCreateMarketIndex as jest.Mock;
const mockUseUpdateMarketIndex = useUpdateMarketIndex as jest.Mock;
const mockUseDeleteMarketIndex = useDeleteMarketIndex as jest.Mock;

describe("CheckinSettings", () => {
  const deleteMutate = jest.fn();

  beforeEach(() => {
    mockUseMarketIndexes.mockReturnValue({
      data: [
        {
          id: "idx-1",
          symbol: "SPX",
          name: "S&P 500",
          tradingview_url: "https://www.tradingview.com/symbols/SPX/",
          is_active: true,
        },
      ],
      isLoading: false,
      isError: false,
    });

    mockUseCreateMarketIndex.mockReturnValue({ mutate: jest.fn(), isPending: false });
    mockUseUpdateMarketIndex.mockReturnValue({ mutate: jest.fn(), isPending: false });
    mockUseDeleteMarketIndex.mockReturnValue({ mutate: deleteMutate, isPending: false });

    deleteMutate.mockClear();
  });

  function renderComponent() {
    const queryClient = new QueryClient();

    return render(
      <QueryClientProvider client={queryClient}>
        <CheckinSettings />
      </QueryClientProvider>
    );
  }

  it("renders only market indexes and hides legacy sections", () => {
    renderComponent();

    expect(screen.getByText("MARKET INDEXES")).toBeInTheDocument();
    expect(screen.queryByText("MARKET PHASES")).not.toBeInTheDocument();
    expect(screen.queryByText("CUSTOM METRICS")).not.toBeInTheDocument();
  });

  it("clicking add button keeps market index form visible with symbol/name/url inputs", () => {
    renderComponent();

    expect(screen.getByPlaceholderText("Symbol (e.g. SPX)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Name")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("TradingView URL")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add Market Index" }));

    expect(screen.getByPlaceholderText("Symbol (e.g. SPX)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Name")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("TradingView URL")).toBeInTheDocument();
  });

  it("deleting market index calls delete hook", () => {
    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(deleteMutate).toHaveBeenCalledWith("idx-1");
  });
});
