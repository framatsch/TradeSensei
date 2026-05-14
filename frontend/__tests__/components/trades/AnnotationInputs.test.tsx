import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnnotationInputs } from "@/components/trades/AnnotationInputs";

const mockDefinitions = [
  { id: "1", name: "Conviction", type: "int" as const, description: null, min_value: 1, max_value: 5, options: null, required: false, scope: "trades" as const, user_id: "u1", created_at: "", updated_at: "", scale_labels: null, icon_identifier: null, is_archived: false },
  { id: "2", name: "Tilt", type: "string_enum" as const, description: null, min_value: null, max_value: null, options: ["Bullish", "Bearish"], required: false, scope: "trades" as const, user_id: "u1", created_at: "", updated_at: "", scale_labels: null, icon_identifier: null, is_archived: false },
  { id: "3", name: "FOMO", type: "bool" as const, description: null, min_value: null, max_value: null, options: null, required: false, scope: "trades" as const, user_id: "u1", created_at: "", updated_at: "", scale_labels: null, icon_identifier: null, is_archived: false },
];

describe("AnnotationInputs", () => {
  it("renders correct input types", () => {
    const onChange = jest.fn();
    render(<AnnotationInputs definitions={mockDefinitions} values={{ "1": 3 }} onChange={onChange} />);

    // int -> number input
    const convictionInput = screen.getByDisplayValue("3");
    expect(convictionInput).toHaveAttribute("type", "number");

    // string_enum -> select
    const tiltSelect = screen.getByRole("combobox");
    expect(tiltSelect).toBeInTheDocument();
    
    // bool -> checkbox
    const fomoCheckbox = screen.getByRole("checkbox");
    expect(fomoCheckbox).toBeInTheDocument();

    // change value
    fireEvent.change(convictionInput, { target: { value: "4" } });
    expect(onChange).toHaveBeenCalledWith({ "1": 4 });
  });

  it("renders empty state", () => {
    render(<AnnotationInputs definitions={[]} values={{}} onChange={jest.fn()} />);
    expect(screen.getByText("No trade annotations found.")).toBeInTheDocument();
  });
});
