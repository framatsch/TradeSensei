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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ImportForm } from "@/components/imports/ImportForm";
import { client } from "@/lib/api/client.gen";
import { useAccounts, useUpdateAccount } from "@/hooks/useAccounts";
import type { Account } from "@/lib/types";

jest.mock("@/hooks/useAccounts", () => ({
  useAccounts: jest.fn(),
  useUpdateAccount: jest.fn(),
}));

jest.mock("@/stores/portfolioStore", () => ({
  usePortfolioStore: (selector: (state: { activePortfolioId: string | null }) => unknown) =>
    selector({ activePortfolioId: "portfolio-1" }),
}));

jest.mock("@/lib/api/client.gen", () => ({
  client: {
    post: jest.fn().mockResolvedValue({
      data: {
        data: {
          imported_count: 0,
          skipped_count: 0,
          errors: [],
        },
      },
      error: null,
    }),
    getConfig: jest.fn().mockReturnValue({ baseUrl: "" }),
  },
}));

const mockUseAccounts = useAccounts as jest.Mock;
const mockUseUpdateAccount = useUpdateAccount as jest.Mock;
const mockClientPost = client.post as jest.Mock;

function makeAccount(overrides: Partial<Account>): Account {
  return {
    id: "account-1",
    user_id: "user-1",
    portfolio_id: "portfolio-1",
    name: "Broker Account",
    account_number: null,
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
    ...overrides,
  };
}

function renderForm() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ImportForm />
    </QueryClientProvider>,
  );
}

describe("ImportForm sync parameter mapping", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-07-18T12:00:00Z"));
    mockUseUpdateAccount.mockReturnValue({
      mutateAsync: jest.fn().mockResolvedValue({}),
      isPending: false,
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("sends from_date for IBKR sync", async () => {
    mockUseAccounts.mockReturnValue({
      data: [makeAccount({ id: "ibkr-account", name: "IBKR Main", type: "ibkr" })],
      isLoading: false,
      isError: false,
    });

    renderForm();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "ibkr-account" } });
    fireEvent.click(screen.getByRole("button", { name: "Sync IBKR Trades" }));

    await waitFor(() => expect(mockClientPost).toHaveBeenCalled());
    const call = mockClientPost.mock.calls[0][0] as { url: string };
    expect(call.url).toContain("/api/v1/broker/sync/ibkr-account?days=");
    expect(call.url).toContain("&from_date=20260101");
  });

  it("sends days only for Schwab sync", async () => {
    mockUseAccounts.mockReturnValue({
      data: [makeAccount({ id: "schwab-account", name: "Schwab IRA", type: "schwab" })],
      isLoading: false,
      isError: false,
    });

    renderForm();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "schwab-account" } });
    fireEvent.click(screen.getByRole("button", { name: "Sync Schwab Trades" }));

    await waitFor(() => expect(mockClientPost).toHaveBeenCalled());
    const call = mockClientPost.mock.calls[0][0] as { url: string };
    expect(call.url).toContain("/api/v1/broker/sync/schwab-account?days=");
    expect(call.url).not.toContain("from_date=");
  });
});
