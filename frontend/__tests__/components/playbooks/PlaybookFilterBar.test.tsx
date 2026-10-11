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
import {
  PlaybookFilterBar,
  DEFAULT_PLAYBOOK_FILTERS,
  type PlaybookFilters,
} from "@/components/playbooks/PlaybookFilterBar";

const mockTaxonomies = [
  { id: "tag-1", name: "Breakout", color_hex: "#10b981", scope: "playbook" },
  { id: "tag-2", name: "Mean Reversion", color_hex: "#3b82f6", scope: "playbook" },
];

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({
    data: mockTaxonomies,
  }),
}));

describe("PlaybookFilterBar", () => {
  const baseCounts = { all: 15, active: 10, inactive: 5 };

  it("renders status tabs with accurate counts", () => {
    const handleChange = jest.fn();
    render(
      <PlaybookFilterBar
        filters={DEFAULT_PLAYBOOK_FILTERS}
        onChange={handleChange}
        totalCounts={baseCounts}
      />
    );

    expect(screen.getByRole("button", { name: "Active (10)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inactive (5)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All (15)" })).toBeInTheDocument();
  });

  it("calls onChange when clicking status tab", async () => {
    const user = userEvent.setup();
    const handleChange = jest.fn();
    render(
      <PlaybookFilterBar
        filters={DEFAULT_PLAYBOOK_FILTERS}
        onChange={handleChange}
        totalCounts={baseCounts}
      />
    );

    await user.click(screen.getByRole("button", { name: "Inactive (5)" }));
    expect(handleChange).toHaveBeenCalledWith({
      ...DEFAULT_PLAYBOOK_FILTERS,
      status: "inactive",
    });
  });

  it("expands filter content on clicking filter toggle and allows searching and tagging", async () => {
    const user = userEvent.setup();
    const handleChange = jest.fn();
    render(
      <PlaybookFilterBar
        filters={DEFAULT_PLAYBOOK_FILTERS}
        onChange={handleChange}
        totalCounts={baseCounts}
      />
    );

    // Filter contents initially not visible
    expect(screen.queryByPlaceholderText("Search by name or description…")).not.toBeInTheDocument();

    // Click filter toggle
    await user.click(screen.getByRole("button", { name: /toggle filter panel/i }));

    // Now search input and tags are visible
    const searchInput = screen.getByPlaceholderText("Search by name or description…");
    expect(searchInput).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Breakout" })).toBeInTheDocument();

    // Type in search
    await user.type(searchInput, "Gap");
    expect(handleChange).toHaveBeenCalledWith({
      ...DEFAULT_PLAYBOOK_FILTERS,
      search: "G",
    });

    // Toggle tag
    await user.click(screen.getByRole("button", { name: "Breakout" }));
    expect(handleChange).toHaveBeenCalledWith({
      ...DEFAULT_PLAYBOOK_FILTERS,
      tagIds: ["tag-1"],
    });
  });

  it("renders active filter count badge and clear all button when filters are active", async () => {
    const user = userEvent.setup();
    const handleChange = jest.fn();
    const activeFilters: PlaybookFilters = {
      status: "inactive",
      tagIds: ["tag-1"],
      search: "test",
    };

    render(
      <PlaybookFilterBar
        filters={activeFilters}
        onChange={handleChange}
        totalCounts={baseCounts}
      />
    );

    // Active count: 1 (status != active) + 1 (tag) + 1 (search) = 3
    expect(screen.getByText("3")).toBeInTheDocument();

    const clearBtn = screen.getByRole("button", { name: /clear all/i });
    expect(clearBtn).toBeInTheDocument();

    await user.click(clearBtn);
    expect(handleChange).toHaveBeenCalledWith(DEFAULT_PLAYBOOK_FILTERS);
  });
});
