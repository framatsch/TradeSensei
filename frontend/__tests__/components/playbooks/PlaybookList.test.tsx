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
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlaybookList } from "@/components/playbooks/PlaybookList";

const mockPush = jest.fn();
const mockUpdatePlaybook = jest.fn();
const mockCreatePlaybook = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const samplePlaybooks = [
  {
    id: "pb-1",
    user_id: "u-1",
    name: "Alpha Breakout",
    description: "Long momentum breakout",
    is_active: true,
    created_at: "2024-01-10T10:00:00Z",
    updated_at: "2024-01-10T10:00:00Z",
    taxonomies: [{ id: "tag-1", name: "Breakout", color_hex: "#10b981" }],
  },
  {
    id: "pb-2",
    user_id: "u-1",
    name: "Zeta Scalp",
    description: "Quick scalp on reversal",
    is_active: false,
    created_at: "2024-02-15T10:00:00Z",
    updated_at: "2024-02-15T10:00:00Z",
    taxonomies: [{ id: "tag-2", name: "Scalp", color_hex: "#f59e0b" }],
  },
];

jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: () => ({
    data: samplePlaybooks,
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useCreatePlaybook: () => ({
    mutate: mockCreatePlaybook,
    isPending: false,
  }),
  useUpdatePlaybook: () => ({
    mutate: mockUpdatePlaybook,
  }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({
    data: [
      { id: "tag-1", name: "Breakout", color_hex: "#10b981" },
      { id: "tag-2", name: "Scalp", color_hex: "#f59e0b" },
    ],
  }),
}));

describe("PlaybookList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders active playbooks by default and does NOT render a delete button in rows", () => {
    render(<PlaybookList />);

    // Default filter is "Active", so Alpha Breakout should be visible
    expect(screen.getByText("Alpha Breakout")).toBeInTheDocument();
    // Inactive playbook should not be visible in default Active view
    expect(screen.queryByText("Zeta Scalp")).not.toBeInTheDocument();

    // Verify Edit button is present
    expect(screen.getByRole("button", { name: "Edit Alpha Breakout" })).toBeInTheDocument();

    // Verify NO Delete button is present in the table
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
  });

  it("toggles status when clicking the status button in the table row", async () => {
    const user = userEvent.setup();
    render(<PlaybookList />);

    const statusBtn = screen.getByRole("button", {
      name: "Toggle status for Alpha Breakout, currently Active",
    });
    expect(statusBtn).toBeInTheDocument();

    await user.click(statusBtn);

    expect(mockUpdatePlaybook).toHaveBeenCalledWith({
      id: "pb-1",
      payload: { is_active: false },
    });
  });

  it("filters to inactive playbooks when Inactive tab is clicked", async () => {
    const user = userEvent.setup();
    render(<PlaybookList />);

    const inactiveTab = screen.getByRole("button", { name: "Inactive (1)" });
    await user.click(inactiveTab);

    // Now Zeta Scalp should be visible, Alpha Breakout hidden
    expect(screen.getByText("Zeta Scalp")).toBeInTheDocument();
    expect(screen.queryByText("Alpha Breakout")).not.toBeInTheDocument();
  });

  it("shows all playbooks when All tab is clicked", async () => {
    const user = userEvent.setup();
    render(<PlaybookList />);

    const allTab = screen.getByRole("button", { name: "All (2)" });
    await user.click(allTab);

    expect(screen.getByText("Alpha Breakout")).toBeInTheDocument();
    expect(screen.getByText("Zeta Scalp")).toBeInTheDocument();
  });

  it("sorts by column header clicking", async () => {
    const user = userEvent.setup();
    render(<PlaybookList />);

    // Switch to All so both items are visible
    await user.click(screen.getByRole("button", { name: "All (2)" }));

    // Click Name sort header to toggle descending
    const nameHeaderBtn = screen.getByRole("button", { name: /name/i });
    await user.click(nameHeaderBtn);

    const rows = screen.getAllByRole("row");
    // After header row, first row should now be Zeta Scalp (descending Z -> A)
    expect(rows[1]).toHaveTextContent("Zeta Scalp");
    expect(rows[2]).toHaveTextContent("Alpha Breakout");
  });
});
