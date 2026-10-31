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
import { BrokerAccountCreateModal } from "@/components/settings/modals/BrokerAccountCreateModal";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as clientGen from "@/lib/api/client.gen";
import * as api from "@/lib/api/index";
import "@testing-library/jest-dom";

jest.mock("@/lib/api/client.gen", () => ({
  client: {
    post: jest.fn().mockResolvedValue({ data: {}, error: null }),
    patch: jest.fn().mockResolvedValue({ data: {}, error: null }),
    get: jest.fn().mockResolvedValue({ data: {}, error: null }),
    delete: jest.fn().mockResolvedValue({ data: {}, error: null }),
  },
}));
jest.mock("@/lib/api/index");
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

describe("BrokerAccountCreateModal", () => {
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
        <BrokerAccountCreateModal
          portfolioId="port-1"
          portfolioName="Day Trading"
          onClose={onClose}
        />
      </QueryClientProvider>
    );
  }

  it("displays target portfolio as read-only text", () => {
    renderComponent();

    expect(screen.getByText("Target Portfolio:")).toBeInTheDocument();
    expect(screen.getByText("Day Trading")).toBeInTheDocument();
  });

  it("renders display name input and broker type select", () => {
    renderComponent();

    expect(screen.getByTestId("account-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("broker-type-select")).toBeInTheDocument();
  });

  it("submit button disabled when name is empty", () => {
    renderComponent();

    expect(screen.getByTestId("submit-create-account")).toBeDisabled();
  });

  it("submit button enabled when name is filled", () => {
    renderComponent();

    fireEvent.change(screen.getByTestId("account-name-input"), {
      target: { value: "My Account" },
    });

    expect(screen.getByTestId("submit-create-account")).not.toBeDisabled();
  });

  it("shows IBKR credential fields when type is IBKR", () => {
    renderComponent();

    expect(screen.getByLabelText("Flex Token")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Flex Query ID")).toHaveAttribute("type", "password");
  });

  it("shows Schwab credential fields when type is changed to Schwab", () => {
    renderComponent();

    fireEvent.change(screen.getByTestId("broker-type-select"), {
      target: { value: "schwab" },
    });

    expect(screen.getByLabelText("App Key")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("App Secret")).toHaveAttribute("type", "password");
    expect(screen.queryByLabelText("Flex Token")).not.toBeInTheDocument();
  });

  it("hides credential section when type is Manual", () => {
    renderComponent();

    fireEvent.change(screen.getByTestId("broker-type-select"), {
      target: { value: "manual" },
    });

    expect(screen.queryByLabelText("Flex Token")).not.toBeInTheDocument();
    expect(screen.getByText("No credentials required for manual accounts")).toBeInTheDocument();
  });

  it("has test connection button", () => {
    renderComponent();

    expect(screen.getByTestId("test-connection-button")).toBeInTheDocument();
  });

  it("test connection button calls test-connection endpoint and shows result", async () => {
    (clientGen.client.post as jest.Mock).mockResolvedValueOnce({
      data: {},
      error: null,
    });

    renderComponent();

    fireEvent.change(screen.getByLabelText("Flex Token"), { target: { value: "test-token" } });
    fireEvent.change(screen.getByLabelText("Flex Query ID"), { target: { value: "test-query" } });
    fireEvent.click(screen.getByTestId("test-connection-button"));

    await waitFor(() => {
      expect(clientGen.client.post).toHaveBeenCalledWith(
        {
          url: "/api/v1/portfolios/port-1/accounts/test-connection",
          body: {
            type: "ibkr",
            properties: { ibkr_flex_token: "test-token", ibkr_flex_query_id: "test-query" },
          },
        }
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Connection successful")).toBeInTheDocument();
    });
  });

  it("test connection failure shows error but save remains enabled", async () => {
    (clientGen.client.post as jest.Mock).mockResolvedValueOnce({
      data: null,
      error: { detail: "Connection failed" },
    });

    renderComponent();

    fireEvent.change(screen.getByTestId("account-name-input"), {
      target: { value: "My Account" },
    });

    fireEvent.click(screen.getByTestId("test-connection-button"));

    await waitFor(() => {
      expect(screen.getByTestId("test-connection-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("submit-create-account")).not.toBeDisabled();
  });

  it("submit calls create account API and closes modal", async () => {
    (api.createAccountApiV1PortfoliosPortfolioIdAccountsPost as jest.Mock).mockResolvedValue({
      data: {},
      error: null,
    });

    renderComponent();

    fireEvent.change(screen.getByTestId("account-name-input"), {
      target: { value: "Test Account" },
    });
    fireEvent.change(screen.getByLabelText("Flex Token"), { target: { value: "test-token" } });
    fireEvent.change(screen.getByLabelText("Flex Query ID"), { target: { value: "test-query" } });
    fireEvent.change(screen.getByLabelText("Sync Start Date"), { target: { value: "2026-01-05" } });

    fireEvent.click(screen.getByTestId("submit-create-account"));

    await waitFor(() => {
      expect(api.createAccountApiV1PortfoliosPortfolioIdAccountsPost).toHaveBeenCalledWith(
        {
          path: { portfolio_id: "port-1" },
          body: {
            name: "Test Account",
            account_number: undefined,
            type: "ibkr",
            properties: { ibkr_flex_token: "test-token", ibkr_flex_query_id: "test-query" },
            portfolio_id: "port-1",
            settings: {
              sync_days: 30,
              flex_from_date_preset: "ytd",
              flex_custom_from_date: "20260105",
            },
          },
        }
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Account created");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("closes on Cancel", () => {
    renderComponent();

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });
});
