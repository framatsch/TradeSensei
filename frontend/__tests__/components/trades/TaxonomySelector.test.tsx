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
import { render, screen, fireEvent } from "@testing-library/react";
import { TaxonomySelector } from "@/components/trades/TaxonomySelector";

const mockTaxonomies = [
  { id: "1", name: "Trend Following", description: null, color_hex: "#000000", scope: "trades", created_at: "", updated_at: "", is_archived: false, icon_identifier: null },
  { id: "2", name: "Reversal", description: null, color_hex: "#ffffff", scope: "trades", created_at: "", updated_at: "", is_archived: false, icon_identifier: null },
];

describe("TaxonomySelector", () => {
  it("renders chips and toggles selection", () => {
    const onChange = jest.fn();
    render(<TaxonomySelector taxonomies={mockTaxonomies} selectedIds={["1"]} onChange={onChange} />);

    const trendFollowingBtn = screen.getByText("Trend Following");
    const reversalBtn = screen.getByText("Reversal");

    expect(trendFollowingBtn).toBeInTheDocument();
    expect(reversalBtn).toBeInTheDocument();

    // Toggle off
    fireEvent.click(trendFollowingBtn);
    expect(onChange).toHaveBeenCalledWith([]);

    // Toggle on
    fireEvent.click(reversalBtn);
    expect(onChange).toHaveBeenCalledWith(["1", "2"]);
  });

  it("renders empty state", () => {
    render(<TaxonomySelector taxonomies={[]} selectedIds={[]} onChange={jest.fn()} />);
    expect(screen.getByText("No trade taxonomies found.")).toBeInTheDocument();
  });
});
