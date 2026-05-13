import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortfolioCreateModal } from "@/components/settings/modals/PortfolioCreateModal";
import { THEME_COLORS } from "@/lib/constants/colors";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as api from "@/lib/api/index";
import "@testing-library/jest-dom";

jest.mock("@/lib/api/index");
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

describe("PortfolioCreateModal", () => {
  let queryClient: QueryClient;
  let onClose: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();
    onClose = jest.fn();
    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <PortfolioCreateModal onClose={onClose} />
      </QueryClientProvider>
    );
  }

  it("renders all form fields", () => {
    renderComponent();

    expect(screen.getByTestId("portfolio-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("currency-select")).toBeInTheDocument();
    expect(screen.getByTestId("currency-warning")).toBeInTheDocument();
  });

  it("currency warning is displayed", () => {
    renderComponent();

    expect(screen.getByTestId("currency-warning")).toHaveTextContent(
      "The base currency cannot be changed after the portfolio is created"
    );
  });

  it("color chip picker shows all THEME_COLORS", () => {
    renderComponent();

    const colorChips = screen.getAllByTestId("color-chip");
    expect(colorChips).toHaveLength(THEME_COLORS.length);
  });

  it("submit button is disabled when name is empty", () => {
    renderComponent();

    const submitButton = screen.getByTestId("submit-create-portfolio");
    expect(submitButton).toBeDisabled();
  });

  it("submit button is enabled when name is filled", () => {
    renderComponent();

    const nameInput = screen.getByTestId("portfolio-name-input");
    fireEvent.change(nameInput, { target: { value: "My Portfolio" } });

    const submitButton = screen.getByTestId("submit-create-portfolio");
    expect(submitButton).not.toBeDisabled();
  });

  it("submit calls createPortfolio API", async () => {
    (api.createPortfolioApiV1PortfoliosPost as jest.Mock).mockResolvedValue({ data: {}, error: null });

    renderComponent();

    const nameInput = screen.getByTestId("portfolio-name-input");
    fireEvent.change(nameInput, { target: { value: "Day Trading" } });

    const targetColorIndex = 2;
    const colorChips = screen.getAllByTestId("color-chip");
    fireEvent.click(colorChips[targetColorIndex]);

    const currencySelect = screen.getByTestId("currency-select");
    fireEvent.change(currencySelect, { target: { value: "EUR" } });

    fireEvent.click(screen.getByTestId("submit-create-portfolio"));

    await waitFor(() => {
      expect(api.createPortfolioApiV1PortfoliosPost).toHaveBeenCalledWith({
        body: {
          name: "Day Trading",
          base_currency: "EUR",
          color_hex: THEME_COLORS[targetColorIndex],
        },
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Portfolio created");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("clicking Cancel calls onClose without API call", () => {
    renderComponent();

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
    expect(api.createPortfolioApiV1PortfoliosPost).not.toHaveBeenCalled();
  });

  it("shows error message on API failure", async () => {
    (api.createPortfolioApiV1PortfoliosPost as jest.Mock).mockResolvedValue({
      data: null,
      error: { detail: "A portfolio with this name already exists" },
    });

    renderComponent();

    const nameInput = screen.getByTestId("portfolio-name-input");
    fireEvent.change(nameInput, { target: { value: "Duplicate" } });

    fireEvent.click(screen.getByTestId("submit-create-portfolio"));

    await waitFor(() => {
      expect(screen.getByTestId("create-error")).toHaveTextContent(
        "A portfolio with this name already exists"
      );
    });
  });
});