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

/**
 * Tests for SchwabConnectionCard component.
 *
 * All three hooks are mocked; date-fns formatDistanceToNow is mocked for
 * deterministic relative time output.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// ── Mock hooks ────────────────────────────────────────────────────────────────
const mockUseSchwabStatus = jest.fn();
const mockSyncNow = jest.fn();
const mockDisconnect = jest.fn();

jest.mock("@/hooks/useSchwabConnection", () => ({
  useSchwabStatus: () => mockUseSchwabStatus(),
  useSchwabSync: () => ({ mutate: mockSyncNow, isPending: false }),
  useDisconnectSchwab: () => ({ mutate: mockDisconnect, isPending: false }),
}));

// ── Mock ConnectSchwabButton to isolate ───────────────────────────────────────
jest.mock("@/components/broker/ConnectSchwabButton", () => ({
  ConnectSchwabButton: () => <button data-testid="connect-schwab-button">Connect Schwab</button>,
}));

// ── Mock date-fns for deterministic output ────────────────────────────────────
jest.mock("date-fns", () => ({
  formatDistanceToNow: () => "2 hours ago",
}));

import { SchwabConnectionCard } from "@/components/broker/SchwabConnectionCard";

describe("SchwabConnectionCard", () => {
  beforeEach(() => {
    mockUseSchwabStatus.mockReset();
    mockSyncNow.mockReset();
    mockDisconnect.mockReset();
    jest.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  // ── Loading state ──────────────────────────────────────────────────────────
  it("renders a loading skeleton when isLoading is true", () => {
    mockUseSchwabStatus.mockReturnValue({ data: undefined, isLoading: true });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("schwab-card-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("schwab-connection-card")).not.toBeInTheDocument();
  });

  // ── Disconnected state ─────────────────────────────────────────────────────
  it("shows 'Not connected' badge when not connected", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: false, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("status-disconnected")).toBeInTheDocument();
    expect(screen.queryByTestId("status-connected")).not.toBeInTheDocument();
  });

  it("shows ConnectSchwabButton when not connected", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: false, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("connect-schwab-button")).toBeInTheDocument();
  });

  it("does not show Sync Now or Disconnect buttons when not connected", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: false, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.queryByTestId("sync-button")).not.toBeInTheDocument();
    expect(screen.queryByTestId("disconnect-button")).not.toBeInTheDocument();
  });

  // ── Connected state ────────────────────────────────────────────────────────
  it("shows 'Connected' badge when connected", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("status-connected")).toBeInTheDocument();
  });

  it("shows 'Never synced' when connected but last_sync_at is null", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("never-synced")).toBeInTheDocument();
  });

  it("shows relative sync time when last_sync_at is set", () => {
    mockUseSchwabStatus.mockReturnValue({
      data: { connected: true, last_sync_at: "2024-01-15T10:00:00Z" },
      isLoading: false,
    });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("last-sync-time")).toBeInTheDocument();
    expect(screen.getByText("2 hours ago")).toBeInTheDocument();
  });

  it("shows Sync Now and Disconnect buttons when connected", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByTestId("sync-button")).toBeInTheDocument();
    expect(screen.getByTestId("disconnect-button")).toBeInTheDocument();
  });

  // ── Sync button ────────────────────────────────────────────────────────────
  it("calls syncNow when Sync Now button is clicked", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    fireEvent.click(screen.getByTestId("sync-button"));
    expect(mockSyncNow).toHaveBeenCalledTimes(1);
  });

  it("shows sync result after successful sync", async () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    mockSyncNow.mockImplementation((_: unknown, { onSuccess }: { onSuccess: (r: unknown) => void }) => {
      onSuccess({ imported_count: 5, skipped_count: 2, errors: [] });
    });
    render(<SchwabConnectionCard />);
    fireEvent.click(screen.getByTestId("sync-button"));
    await waitFor(() => {
      expect(screen.getByTestId("sync-result")).toBeInTheDocument();
      expect(screen.getByText(/5 trades imported/i)).toBeInTheDocument();
      expect(screen.getByText(/2 skipped/i)).toBeInTheDocument();
    });
  });

  it("shows sync error on failure", async () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    mockSyncNow.mockImplementation((_: unknown, { onError }: { onError: (e: { message: string }) => void }) => {
      onError({ message: "Token expired" });
    });
    render(<SchwabConnectionCard />);
    fireEvent.click(screen.getByTestId("sync-button"));
    await waitFor(() => {
      expect(screen.getByTestId("sync-error")).toHaveTextContent("Token expired");
    });
  });

  // ── Disconnect button ──────────────────────────────────────────────────────
  it("calls disconnect when user confirms the disconnect dialog", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    fireEvent.click(screen.getByTestId("disconnect-button"));
    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(mockDisconnect).toHaveBeenCalledTimes(1);
  });

  it("does not call disconnect when user cancels the confirm dialog", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: true, last_sync_at: null }, isLoading: false });
    jest.spyOn(window, "confirm").mockReturnValue(false);
    render(<SchwabConnectionCard />);
    fireEvent.click(screen.getByTestId("disconnect-button"));
    expect(mockDisconnect).not.toHaveBeenCalled();
  });

  // ── Card structure ─────────────────────────────────────────────────────────
  it("renders the Schwab heading and description", () => {
    mockUseSchwabStatus.mockReturnValue({ data: { connected: false, last_sync_at: null }, isLoading: false });
    render(<SchwabConnectionCard />);
    expect(screen.getByText("Schwab")).toBeInTheDocument();
    expect(screen.getByText(/charles schwab brokerage/i)).toBeInTheDocument();
  });
});
