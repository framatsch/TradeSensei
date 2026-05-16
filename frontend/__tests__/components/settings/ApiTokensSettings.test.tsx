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
import { ApiTokensSettings } from "@/components/settings/ApiTokensSettings";
import {
  useApiTokens,
  useCreateApiToken,
  useRevokeApiToken,
} from "@/hooks/useApiTokens";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom";

jest.mock("@/hooks/useApiTokens");

const mockUseApiTokens = useApiTokens as jest.Mock;
const mockUseCreateApiToken = useCreateApiToken as jest.Mock;
const mockUseRevokeApiToken = useRevokeApiToken as jest.Mock;

const mockTokens = [
  {
    id: "tok-1",
    name: "Claude Desktop",
    created_at: "2026-01-01T00:00:00Z",
    expires_at: "2030-01-01T00:00:00Z",
    is_revoked: false,
    last_used_at: "2026-05-01T12:00:00Z",
  },
  {
    id: "tok-2",
    name: "Cursor Local",
    created_at: "2026-02-01T00:00:00Z",
    expires_at: "2026-03-01T00:00:00Z",
    is_revoked: false,
    last_used_at: null,
  },
  {
    id: "tok-3",
    name: "Old Integration",
    created_at: "2025-06-01T00:00:00Z",
    expires_at: "2030-01-01T00:00:00Z",
    is_revoked: true,
    last_used_at: "2025-10-01T00:00:00Z",
  },
];

describe("ApiTokensSettings", () => {
  let queryClient: QueryClient;
  let mockRevokeAsync: jest.Mock;
  let mockCreateAsync: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();
    mockRevokeAsync = jest.fn().mockResolvedValue(undefined);
    mockCreateAsync = jest.fn();

    mockUseApiTokens.mockReturnValue({
      data: mockTokens,
      isLoading: false,
      isError: false,
      error: null,
    });
    mockUseCreateApiToken.mockReturnValue({
      mutateAsync: mockCreateAsync,
      isPending: false,
    });
    mockUseRevokeApiToken.mockReturnValue({
      mutateAsync: mockRevokeAsync,
    });

    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <ApiTokensSettings />
      </QueryClientProvider>
    );
  }

  describe("rendering", () => {
    it("renders header and description", () => {
      renderComponent();
      expect(screen.getByText("API & Tokens")).toBeInTheDocument();
      expect(
        screen.getByText(/Generate personal access tokens for MCP integrations/)
      ).toBeInTheDocument();
      expect(screen.getByText("What can I do with MCP?")).toBeInTheDocument();
    });

    it("shows MCP examples when expanded", () => {
      renderComponent();
      fireEvent.click(screen.getByText("What can I do with MCP?"));
      expect(screen.getByText(/Performance discovery:/)).toBeInTheDocument();
      expect(screen.getByText("Learn more")).toBeInTheDocument();
    });

    it("renders Generate New Token button", () => {
      renderComponent();
      expect(screen.getByText("Generate New Token")).toBeInTheDocument();
    });

    it("renders token table with correct columns", () => {
      renderComponent();
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Created")).toBeInTheDocument();
      expect(screen.getByText("Expires")).toBeInTheDocument();
      expect(screen.getByText("Last Used")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Action")).toBeInTheDocument();
    });

    it("renders token names in the table", () => {
      renderComponent();
      expect(screen.getByText("Claude Desktop")).toBeInTheDocument();
      expect(screen.getByText("Cursor Local")).toBeInTheDocument();
      expect(screen.getByText("Old Integration")).toBeInTheDocument();
    });

    it("renders Active status badge for active tokens", () => {
      renderComponent();
      const activeBadges = screen.getAllByText("Active");
      expect(activeBadges.length).toBe(1);
    });

    it("renders Expired status badge for expired tokens", () => {
      renderComponent();
      expect(screen.getByText("Expired")).toBeInTheDocument();
    });

    it("renders Revoked status badge for revoked tokens", () => {
      renderComponent();
      expect(screen.getByText("Revoked")).toBeInTheDocument();
    });

    it("renders Revoke button for active tokens", () => {
      renderComponent();
      expect(screen.getByText("Revoke")).toBeInTheDocument();
    });

    it("does not render Revoke button for expired tokens", () => {
      renderComponent();
      const revokeButtons = screen.getAllByText("Revoke");
      expect(revokeButtons.length).toBe(1);
      const dashSpans = screen.getAllByText("-");
      expect(dashSpans.length).toBe(3);
    });
  });

  describe("loading state", () => {
    it("shows spinner while tokens are loading", () => {
      mockUseApiTokens.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      });
      renderComponent();
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message on fetch failure", () => {
      mockUseApiTokens.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("Network error"),
      });
      renderComponent();
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows empty message when no tokens exist", () => {
      mockUseApiTokens.mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      });
      renderComponent();
      expect(
        screen.getByText(/No tokens yet/)
      ).toBeInTheDocument();
    });
  });

  describe("GenerateTokenModal", () => {
    it("opens modal when Generate New Token is clicked", () => {
      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));
      expect(screen.getAllByText("Generate New Token")).toHaveLength(2);
      expect(screen.getByPlaceholderText("e.g. Claude Desktop")).toBeInTheDocument();
    });

    it("closes modal when Cancel is clicked", () => {
      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));
      fireEvent.click(screen.getByText("Cancel"));
      expect(
        screen.queryByPlaceholderText("e.g. Claude Desktop")
      ).not.toBeInTheDocument();
    });

    it("shows validation error on empty name", async () => {
      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));
      fireEvent.click(screen.getByText("Generate"));
      await waitFor(() => {
        expect(screen.getByText("Token name is required.")).toBeInTheDocument();
      });
    });

    it("submits and calls onCreated on success", async () => {
      const createdToken = {
        id: "tok-new",
        name: "New Client",
        created_at: "2026-05-02T00:00:00Z",
        expires_at: "2026-08-01T00:00:00Z",
        is_revoked: false,
        last_used_at: null,
        token: "pat_abc123",
      };
      mockCreateAsync.mockResolvedValue(createdToken);

      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));

      const nameInput = screen.getByPlaceholderText("e.g. Claude Desktop");
      fireEvent.change(nameInput, { target: { value: "New Client" } });

      fireEvent.click(screen.getByText("Generate"));

      await waitFor(() => {
        expect(mockCreateAsync).toHaveBeenCalled();
      });
      expect(screen.getByText("Save this token now. You will not be able to see it again.")).toBeInTheDocument();
    });
  });

  describe("TokenDisplayModal", () => {
    it("shows token code and warning", async () => {
      const createdToken = {
        id: "tok-new",
        name: "New Client",
        created_at: "2026-05-02T00:00:00Z",
        expires_at: "2026-08-01T00:00:00Z",
        is_revoked: false,
        last_used_at: null,
        token: "pat_abc123",
      };
      mockCreateAsync.mockResolvedValue(createdToken);

      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));

      const nameInput = screen.getByPlaceholderText("e.g. Claude Desktop");
      fireEvent.change(nameInput, { target: { value: "New Client" } });
      fireEvent.click(screen.getByText("Generate"));

      await waitFor(() => {
        expect(mockCreateAsync).toHaveBeenCalled();
      });
      expect(screen.getByText("pat_abc123")).toBeInTheDocument();
      expect(
        screen.getByText("Save this token now. You will not be able to see it again.")
      ).toBeInTheDocument();
      expect(screen.getByText("Copy")).toBeInTheDocument();
      expect(screen.getByText("Close")).toBeInTheDocument();
    });

    it("closes TokenDisplayModal when Close is clicked", async () => {
      const createdToken = {
        id: "tok-new",
        name: "New Client",
        created_at: "2026-05-02T00:00:00Z",
        expires_at: "2026-08-01T00:00:00Z",
        is_revoked: false,
        last_used_at: null,
        token: "pat_abc123",
      };
      mockCreateAsync.mockResolvedValue(createdToken);

      renderComponent();
      fireEvent.click(screen.getByText("Generate New Token"));
      fireEvent.change(screen.getByPlaceholderText("e.g. Claude Desktop"), {
        target: { value: "New Client" },
      });
      fireEvent.click(screen.getByText("Generate"));

      await waitFor(() => {
        expect(mockCreateAsync).toHaveBeenCalled();
      });
      expect(screen.getByText("pat_abc123")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Close"));

      await waitFor(() => {
        expect(screen.queryByText("pat_abc123")).not.toBeInTheDocument();
      });
    });
  });

  describe("token revocation", () => {
    it("calls revoke when Revoke button is clicked", async () => {
      window.confirm = jest.fn(() => true);

      renderComponent();
      fireEvent.click(screen.getByText("Revoke"));

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith(
          'Revoke token "Claude Desktop"?'
        );
        expect(mockRevokeAsync).toHaveBeenCalledWith("tok-1");
      });
    });

    it("does not revoke when confirm is cancelled", async () => {
      window.confirm = jest.fn(() => false);

      renderComponent();
      fireEvent.click(screen.getByText("Revoke"));

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalled();
        expect(mockRevokeAsync).not.toHaveBeenCalled();
      });
    });
  });
});
