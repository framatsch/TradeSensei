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
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AccountList } from "@/components/accounts/AccountList";
import type { ClearTradesResult } from "@/lib/api/types.gen";
import type { Account } from "@/lib/types";
import { useClearAccountTrades, useDeleteAccount } from "@/hooks/useAccounts";
import toast from "react-hot-toast";

jest.mock("@/hooks/useAccounts", () => ({
  useDeleteAccount: jest.fn(),
  useClearAccountTrades: jest.fn(),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const mockUseDeleteAccount = useDeleteAccount as jest.Mock;
const mockUseClearAccountTrades = useClearAccountTrades as jest.Mock;

const account: Account = {
  id: "account-1",
  user_id: "user-1",
  portfolio_id: "portfolio-1",
  name: "Primary IBKR",
  account_number: "U12345",
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

describe("AccountList clear-trades flow", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseDeleteAccount.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
    });
  });

  it("requires typed confirmation before clearing trades", () => {
    const clearMutate = jest.fn();
    mockUseClearAccountTrades.mockReturnValue({
      mutate: clearMutate,
      isPending: false,
    });

    render(<AccountList accounts={[account]} />);

    fireEvent.click(screen.getByRole("button", { name: "Clear Trades" }));
    const clearButton = screen.getByRole("button", { name: "Clear All Trades" });

    expect(clearButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(`Type ${account.name} to confirm:`), {
      target: { value: account.name },
    });

    expect(clearButton).toBeEnabled();
  });

  it("shows success toast and closes modal after clearing trades", async () => {
    const clearMutate = jest.fn(
      (
        accountId: string,
        options?: {
          onSuccess?: (value: ClearTradesResult) => void;
          onError?: (err: Error) => void;
        },
      ) => {
        expect(accountId).toBe(account.id);
        options?.onSuccess?.({ trades_deleted: 2, executions_deleted: 1 });
      },
    );

    mockUseClearAccountTrades.mockReturnValue({
      mutate: clearMutate,
      isPending: false,
    });

    render(<AccountList accounts={[account]} />);

    fireEvent.click(screen.getByRole("button", { name: "Clear Trades" }));
    fireEvent.change(screen.getByLabelText(`Type ${account.name} to confirm:`), {
      target: { value: account.name },
    });
    fireEvent.click(screen.getByRole("button", { name: "Clear All Trades" }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        "Cleared 2 trades and 1 executions from Primary IBKR.",
      );
    });
    expect(screen.queryByText("Danger Zone")).not.toBeInTheDocument();
  });
});
