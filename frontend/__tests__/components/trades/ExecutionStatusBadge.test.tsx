import React from "react";
import { render, screen } from "@testing-library/react";
import { ExecutionStatusBadge } from "@/components/trades/ExecutionStatusBadge";

describe("ExecutionStatusBadge", () => {
  it("renders split child label when parent_id exists", () => {
    render(
      <ExecutionStatusBadge
        origin="split"
        deleted={false}
        user_modified={false}
        parent_id="5b0df4f8-c583-447f-a934-8d39d1fd8272"
      />
    );

    expect(screen.getByText("Split Child")).toBeInTheDocument();
  });

  it("renders split label when parent_id is missing", () => {
    render(<ExecutionStatusBadge origin="split" deleted={false} user_modified={false} parent_id={null} />);

    expect(screen.getByText("Split")).toBeInTheDocument();
  });
});
