import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ChartDisplaySettings } from "@/components/settings/ChartDisplaySettings";
import { useSettings, useUpdateSettings } from "@/hooks/useSettings";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import "@testing-library/jest-dom";

jest.mock("@/hooks/useSettings");
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const mockUseSettings = useSettings as jest.Mock;
const mockUseUpdateSettings = useUpdateSettings as jest.Mock;

describe("ChartDisplaySettings", () => {
  let queryClient: QueryClient;
  let mockMutateAsync: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();
    mockMutateAsync = jest.fn().mockResolvedValue({});
    mockUseSettings.mockReturnValue({
      data: {
        chart_candles_before: 15,
        chart_candles_after: 5,
        chart_show_post_exit: true,
        home_route: "/dashboard/trades",
      },
      isLoading: false,
    });
    mockUseUpdateSettings.mockReturnValue({
      mutateAsync: mockMutateAsync,
    });
    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <ChartDisplaySettings />
      </QueryClientProvider>
    );
  }

  it("renders saved values", () => {
    renderComponent();

    // Since labels aren't explicitly linked in the code, we find inputs by their default value.
    expect(screen.getByDisplayValue("15")).toBeInTheDocument();
    expect(screen.getByDisplayValue("5")).toBeInTheDocument();
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
    expect(screen.getByDisplayValue("Journal")).toBeInTheDocument();
  });

  it("shows validation error on <= 0 input", async () => {
    renderComponent();

    const beforeInput = screen.getByDisplayValue("15");
    fireEvent.change(beforeInput, { target: { value: "0" } });

    const saveButton = screen.getByRole("button", { name: "Save Settings" });
    fireEvent.click(saveButton);

    expect(screen.getByText("Candles before entry must be a positive whole number")).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("calls useUpdateSettings on valid save", async () => {
    renderComponent();

    const beforeInput = screen.getByDisplayValue("15");
    fireEvent.change(beforeInput, { target: { value: "30" } });

    const saveButton = screen.getByRole("button", { name: "Save Settings" });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        chart_candles_before: 30,
        chart_candles_after: 5,
        chart_show_post_exit: true,
        home_route: "/dashboard/trades",
      });
      expect(toast.success).toHaveBeenCalledWith("Settings saved successfully");
    });
  });
});
