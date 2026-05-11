import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { TaxonomySelector } from "@/components/trades/TaxonomySelector";

const mockTaxonomies = [
  { id: "1", name: "Trend Following", description: null, color: null, user_id: "u1", scope: "both", created_at: "", updated_at: "" },
  { id: "2", name: "Reversal", description: null, color: null, user_id: "u1", scope: "both", created_at: "", updated_at: "" },
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
