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
