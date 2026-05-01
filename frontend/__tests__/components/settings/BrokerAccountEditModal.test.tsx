import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrokerAccountEditModal } from "@/components/settings/modals/BrokerAccountEditModal";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { toast } from "react-hot-toast";
import * as clientGen from "@/lib/api/client.gen";
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
  });

  function renderComponent(account = mockAccount) {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrokerAccountEditModal account={account} onClose={onClose} />
      </QueryClientProvider>
    );
  }

  it("renders with pre-filled name", () => {
    renderComponent();

    const nameInput = screen.getByTestId("edit-account-name-input") as HTMLInputElement;
    expect(nameInput.value).toBe("IBKR Main");
  });

  it("broker type is shown as immutable badge, not a select", () => {
    renderComponent();

    expect(screen.getByTestId("immutable-broker-type")).toHaveTextContent("IBKR");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("credential fields are rendered as password inputs with empty values", () => {
    renderComponent();

    const tokenInput = screen.getByTestId("credential-IBKR_FLEX_TOKEN") as HTMLInputElement;
    const queryInput = screen.getByTestId("credential-IBKR_FLEX_QUERY_ID") as HTMLInputElement;

    expect(tokenInput.type).toBe("password");
    expect(tokenInput.value).toBe("");
    expect(queryInput.type).toBe("password");
    expect(queryInput.value).toBe("");
  });

  it("shows hint text to leave blank to keep existing credentials", () => {
    renderComponent();

    expect(screen.getByText("Leave blank to keep existing credentials")).toBeInTheDocument();
  });

  it("shows test connection button", () => {
    renderComponent();

    expect(screen.getByTestId("edit-test-connection-button")).toBeInTheDocument();
  });

  it("shows Deactivate Account button when account is active", () => {
    renderComponent();

    expect(screen.getByTestId("deactivate-button")).toHaveTextContent("Deactivate Account");
  });

  it("shows Reactivate Account button when account is inactive", () => {
    renderComponent(mockInactiveAccount);

    expect(screen.getByTestId("reactivate-button")).toHaveTextContent("Reactivate Account");
  });

  it("deactivate button toggles is_active to false", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    renderComponent();

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

    renderComponent(mockInactiveAccount);

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

    renderComponent();

    fireEvent.change(screen.getByTestId("edit-account-name-input"), {
      target: { value: "Updated Name" },
    });

    fireEvent.click(screen.getByTestId("save-edit-account"));

    await waitFor(() => {
      expect(api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch).toHaveBeenCalledWith(
        expect.objectContaining({
          path: { portfolio_id: "port-1", account_id: "acct-1" },
          body: { name: "Updated Name" },
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Account updated");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("no delete button exists in the modal", () => {
    renderComponent();

    expect(screen.queryByText(/delete/i)).not.toBeInTheDocument();
  });

  it("does not propagate credentials if left empty on save", async () => {
    (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mockResolvedValue({ data: {}, error: null });

    renderComponent();

    fireEvent.click(screen.getByTestId("save-edit-account"));

    await waitFor(() => {
      const call = (api.updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch as jest.Mock).mock.calls[0][0];
      expect(call.body).not.toHaveProperty("properties");
    });
  });
});