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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SchwabConnectSection } from "@/components/settings/modals/SchwabConnectSection";
import * as api from "@/lib/api/index";

jest.mock("@/lib/api/index");

// Mock react-hot-toast
jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));
import { toast } from "react-hot-toast";

describe("SchwabConnectSection", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });
    jest.clearAllMocks();
    jest.spyOn(window, "open").mockImplementation(() => null);
  });

  const renderComponent = (account = { id: "acc-123" }) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <SchwabConnectSection account={account as any} />
      </QueryClientProvider>
    );
  };

  it("shows loading state initially", () => {
    (api.getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet as jest.Mock).mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getByText("Checking connection status...")).toBeInTheDocument();
  });

  it("shows disconnected state and handles connect button", async () => {
    (api.getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet as jest.Mock).mockResolvedValue({
      data: { data: { connected: false } },
    });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    // Click connect
    (api.startSchwabAuthorizationApiV1BrokerSchwabAuthorizeAccountIdPost as jest.Mock).mockResolvedValue({
      data: { data: { authorization_url: "https://auth.schwab.com/url" } },
    });

    fireEvent.click(screen.getByRole("button", { name: /Connect Schwab/i }));

    await waitFor(() => {
      expect(api.startSchwabAuthorizationApiV1BrokerSchwabAuthorizeAccountIdPost).toHaveBeenCalledWith({
        path: { account_id: "acc-123" }
      });
      expect(window.open).toHaveBeenCalledWith("https://auth.schwab.com/url", "_blank");
    });
  });

  it("handles paste flow submission", async () => {
    (api.getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet as jest.Mock).mockResolvedValue({
      data: { data: { connected: false } },
    });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    (api.completeSchwabConnectionApiV1BrokerSchwabCompleteAccountIdPost as jest.Mock).mockResolvedValue({
      data: { data: { success: true } },
    });

    const input = screen.getByPlaceholderText("https://127.0.0.1/?code=...&state=...");
    fireEvent.change(input, { target: { value: "https://localhost/?code=abc" } });
    
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => {
      expect(api.completeSchwabConnectionApiV1BrokerSchwabCompleteAccountIdPost).toHaveBeenCalledWith({
        path: { account_id: "acc-123" },
        body: { redirect_url: "https://localhost/?code=abc" }
      });
      expect(toast.success).toHaveBeenCalledWith("Schwab account connected");
    });
  });

  it("shows connected state and handles disconnect button", async () => {
    (api.getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet as jest.Mock).mockResolvedValue({
      data: { data: { connected: true } },
    });
    
    renderComponent();
    
    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    (api.disconnectSchwabApiV1BrokerSchwabConnectAccountIdDelete as jest.Mock).mockResolvedValue({
      data: { data: { success: true } },
    });

    fireEvent.click(screen.getByRole("button", { name: /Disconnect/i }));

    await waitFor(() => {
      expect(api.disconnectSchwabApiV1BrokerSchwabConnectAccountIdDelete).toHaveBeenCalledWith({
        path: { account_id: "acc-123" }
      });
      expect(toast.success).toHaveBeenCalledWith("Schwab account disconnected");
    });
  });
});
