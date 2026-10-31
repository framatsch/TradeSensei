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
import { act, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrokerAccountEditModal } from "@/components/settings/modals/BrokerAccountEditModal";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as api from "@/lib/api/index";
import type { Account } from "@/lib/types";
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

const mockAccount: Account = {
  id: "acct-1",
  user_id: "user-1",
  portfolio_id: "port-1",
  name: "IBKR Main",
  account_number: "U123",
  type: "ibkr",
  currency: "USD",
  is_active: true,
  has_api_keys: true,
  settings: {
    sync_days: 30,
    flex_from_date_preset: "ytd",
    flex_custom_from_date: null,
  },
  created_at: "2024-01-01T00:00:00Z",
};

const mockInactiveAccount: Account = {
  ...mockAccount,
  is_active: false,
};

describe("BrokerAccountEditModal", () => {
  let queryClient: QueryClient;
  let onClose: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();
    onClose = jest.fn();
    jest.clearAllMocks();
    (api.getAccountCredentialsApiV1PortfoliosPortfolioIdAccountsAccountIdCredentialsGet as jest.Mock)
      .mockResolvedValue({ data: { data: { properties: {} } }, error: null });
  });

  async function renderComponent(account = mockAccount) {
    await act(async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <BrokerAccountEditModal account={account} onClose={onClose} />
        </QueryClientProvider>
      );
    });
  }

  it("renders with pre-filled name", async () => {
    await renderComponent();

    const nameInput = screen.getByTestId("edit-account-name-input") as HTMLInputElement;
    expect(nameInput.value).toBe("IBKR Main");
  });

  it("broker type is shown as immutable badge, not a select", async () => {
    await renderComponent();

    expect(screen.getByTestId("immutable-broker-type")).toHaveTextContent("IBKR");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("credential fields are masked and empty when no stored credentials are returned", async () => {
    await renderComponent();

    const tokenInput = screen.getByLabelText("Flex Token");
    const queryInput = screen.getByLabelText("Flex Query ID");

    expect(tokenInput).toHaveAttribute("type", "password");
    expect(tokenInput).toHaveValue("");
    expect(queryInput).toHaveAttribute("type", "password");
    expect(queryInput).toHaveValue("");
    expect(api.getAccountCredentialsApiV1PortfoliosPortfolioIdAccountsAccountIdCredentialsGet)
      .toHaveBeenCalledWith({ path: { portfolio_id: "port-1", account_id: "acct-1" } });
  });

  it("loads stored credentials for review and masks them until explicitly revealed", async () => {
    (api.getAccountCredentialsApiV1PortfoliosPortfolioIdAccountsAccountIdCredentialsGet as jest.Mock)
      .mockResolvedValue({
        data: { data: { properties: { IBKR_FLEX_TOKEN: "stored-token", IBKR_FLEX_QUERY_ID: "stored-query" } } },
        error: null,
      });
    await renderComponent();

    expect(screen.getByText("Stored credentials are loaded for review and can be edited.")).toBeInTheDocument();
    expect(screen.getByLabelText("Flex Token")).toHaveValue("stored-token");
    expect(screen.getByLabelText("Flex Query ID")).toHaveValue("stored-query");
    expect(screen.getByLabelText("Flex Token")).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("button", { name: "Show Flex Token" }));
    expect(screen.getByLabelText("Flex Token")).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: "Hide Flex Token" }));
    expect(screen.getByLabelText("Flex Token")).toHaveAttribute("type", "password");
  });

  it("shows test connection button", async () => {
    await renderComponent();

    expect(screen.getByTestId("edit-test-connection-button")).toBeInTheDocument();
  });

  it("shows Deactivate Account button when account is active", async () => {
    await renderComponent();

    expect(screen.getByTestId("deactivate-button")).toHaveTextContent("Deactivate Account");
  });

  it("shows Reactivate Account button when account is inactive", async () => {
    await renderComponent(mockInactiveAccount);

    expect(screen.getByTestId("reactivate-button")).toHaveTextContent("Reactivate Account");
  });

  it("deactivate button toggles is_active to false", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    await renderComponent();

    fireEvent.click(screen.getByTestId("deactivate-button"));

    await waitFor(() => {
      expect(api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch).toHaveBeenCalledWith(
        expect.objectContaining({
          path: { portfolio_id: "port-1", account_id: "acct-1" },
          body: { is_active: false },
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Account deactivated");
    });
  });

  it("reactivate button toggles is_active to true", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    await renderComponent(mockInactiveAccount);

    fireEvent.click(screen.getByTestId("reactivate-button"));

    await waitFor(() => {
      expect(api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch).toHaveBeenCalledWith(
        expect.objectContaining({
          body: { is_active: true },
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Account reactivated");
    });
  });

  it("save submits name only when no credentials entered", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    await renderComponent();

    fireEvent.change(screen.getByTestId("edit-account-name-input"), {
      target: { value: "Updated Name" },
    });

    fireEvent.click(screen.getByTestId("save-edit-account"));

    await waitFor(() => {
      expect(api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch).toHaveBeenCalledWith(
        expect.objectContaining({
          path: { portfolio_id: "port-1", account_id: "acct-1" },
          body: { name: "Updated Name", account_number: "U123" },
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Account updated");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("keeps delete actions hidden until the danger zone is expanded and confirmed", async () => {
    await renderComponent();

    expect(screen.queryByRole("button", { name: "Delete Account" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show Danger Zone" }));
    expect(screen.getByRole("button", { name: "Delete Account" })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("IBKR Main"), { target: { value: "IBKR Main" } });
    expect(screen.getByRole("button", { name: "Delete Account" })).toBeEnabled();
  });

  it("does not propagate credentials if left empty on save", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    await renderComponent();

    fireEvent.click(screen.getByTestId("save-edit-account"));

    await waitFor(() => {
      const call = (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mock.calls[0][0];
      expect(call.body).not.toHaveProperty("properties");
    });
  });
});
