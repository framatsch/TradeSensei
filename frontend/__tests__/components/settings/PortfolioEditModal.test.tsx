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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortfolioEditModal } from "@/components/settings/modals/PortfolioEditModal";
import { THEME_COLORS } from "@/lib/constants/colors";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as api from "@/lib/api/index";
import "@testing-library/jest-dom";

import { PortfolioRead } from "@/lib/api";

jest.mock("@/lib/api/index");
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const mockPortfolio: PortfolioRead = {
  id: "port-1",
  user_id: "user-1",
  name: "Day Trading",
  base_currency: "USD",
  color_hex: THEME_COLORS[4],
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

describe("PortfolioEditModal", () => {
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
        <PortfolioEditModal portfolio={mockPortfolio} onClose={onClose} />
      </QueryClientProvider>
    );
  }

  it("renders with pre-filled name and selected color chip", () => {
    renderComponent();

    const nameInput = screen.getByTestId("edit-portfolio-name-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Day Trading");
  });

  it("base currency is displayed as read-only badge", () => {
    renderComponent();

    expect(screen.getByTestId("readonly-currency")).toHaveTextContent("USD");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("danger zone delete button is disabled until name matches", () => {
    renderComponent();

    const deleteButton = screen.getByTestId("delete-portfolio-button");
    expect(deleteButton).toBeDisabled();

    const confirmInput = screen.getByTestId("delete-confirm-input");
    fireEvent.change(confirmInput, { target: { value: "wrong name" } });
    expect(deleteButton).toBeDisabled();
  });

  it("danger zone delete button is enabled when confirm name matches (case-sensitive)", () => {
    renderComponent();

    const confirmInput = screen.getByTestId("delete-confirm-input");
    fireEvent.change(confirmInput, { target: { value: "Day Trading" } });

    const deleteButton = screen.getByTestId("delete-portfolio-button");
    expect(deleteButton).not.toBeDisabled();
  });

  it("danger zone delete button remains disabled with wrong case", () => {
    renderComponent();

    const confirmInput = screen.getByTestId("delete-confirm-input");
    fireEvent.change(confirmInput, { target: { value: "day trading" } });

    const deleteButton = screen.getByTestId("delete-portfolio-button");
    expect(deleteButton).toBeDisabled();
  });

  it("danger zone shows warning text", () => {
    renderComponent();

    const dangerZone = screen.getByTestId("danger-zone");
    expect(dangerZone).toHaveTextContent("This will permanently delete this portfolio");
    expect(dangerZone).toHaveTextContent("This action cannot be undone");
  });

  it("calls delete API when confirm name matches and button clicked", async () => {
    (api.deletePortfolioApiV1PortfoliosPortfolioIdDelete as jest.Mock).mockResolvedValue({
      data: {},
      error: null,
    });

    renderComponent();

    const confirmInput = screen.getByTestId("delete-confirm-input");
    fireEvent.change(confirmInput, { target: { value: "Day Trading" } });

    fireEvent.click(screen.getByTestId("delete-portfolio-button"));

    await waitFor(() => {
      expect(api.deletePortfolioApiV1PortfoliosPortfolioIdDelete).toHaveBeenCalledWith({
        path: { portfolio_id: "port-1" },
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Portfolio deleted");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("save calls updatePortfolio API with name and color", async () => {
    (api.updatePortfolioApiV1PortfoliosPortfolioIdPatch as jest.Mock).mockResolvedValue({
      data: {},
      error: null,
    });

    renderComponent();

    const nameInput = screen.getByTestId("edit-portfolio-name-input");
    fireEvent.change(nameInput, { target: { value: "New Name" } });

    const colorChips = screen.getAllByTestId("color-chip");
    fireEvent.click(colorChips[7]);

    fireEvent.click(screen.getByTestId("save-edit-portfolio"));

    await waitFor(() => {
      expect(api.updatePortfolioApiV1PortfoliosPortfolioIdPatch).toHaveBeenCalledWith({
        path: { portfolio_id: "port-1" },
        body: {
          name: "New Name",
          color_hex: THEME_COLORS[7],
        },
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Portfolio updated");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("calls onClose when cancel is clicked", () => {
    renderComponent();

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });
});