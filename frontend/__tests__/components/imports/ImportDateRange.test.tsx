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
import { fireEvent, render, screen } from "@testing-library/react";
import { ImportDateRange } from "@/components/imports/ImportDateRange";
import type { BrokerImportCapability } from "@/components/imports/ImportCapability";

describe("ImportDateRange", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date("2026-07-18T12:00:00Z"));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders unified fill-bar control and emits from_date-compatible value for IBKR", () => {
    const onPresetChange = jest.fn();
    const onCustomFromDateChange = jest.fn();
    const capability: BrokerImportCapability = {
      maxWindowDays: 365,
      syncParam: { kind: "fromDate" },
    };

    render(
      <ImportDateRange
        capability={capability}
        preset="ytd"
        customFromDate="20260101"
        onPresetChange={onPresetChange}
        onCustomFromDateChange={onCustomFromDateChange}
      />,
    );

    expect(screen.getByRole("button", { name: /YTD/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Custom date/i }));
    expect(onPresetChange).toHaveBeenCalledWith("custom");
  });

  it("renders with Schwab capability and keeps unified date-range controls", () => {
    const onPresetChange = jest.fn();
    const onCustomFromDateChange = jest.fn();
    const capability: BrokerImportCapability = {
      maxWindowDays: 365,
      syncParam: { kind: "days" },
    };

    render(
      <ImportDateRange
        capability={capability}
        preset="ytd"
        customFromDate="20260101"
        onPresetChange={onPresetChange}
        onCustomFromDateChange={onCustomFromDateChange}
      />,
    );

    expect(screen.getByRole("button", { name: /YTD/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Custom date/i })).toBeInTheDocument();
    expect(screen.getByText(/Max\. 365 days/i)).toBeInTheDocument();
    expect(onPresetChange).not.toHaveBeenCalled();
    expect(onCustomFromDateChange).not.toHaveBeenCalled();
  });

  it("clamps custom date input to capability max window", () => {
    const onPresetChange = jest.fn();
    const onCustomFromDateChange = jest.fn();
    const capability: BrokerImportCapability = {
      maxWindowDays: 365,
      syncParam: { kind: "fromDate" },
    };

    render(
      <ImportDateRange
        capability={capability}
        preset="custom"
        customFromDate="20240101"
        onPresetChange={onPresetChange}
        onCustomFromDateChange={onCustomFromDateChange}
      />,
    );

    const dateInput = screen.getByDisplayValue("2024-01-01") as HTMLInputElement;
    expect(dateInput.min).toBe("2025-07-18");
    expect(dateInput.max).toBe("2026-07-18");
    expect(screen.getByText(/Max\. 365 days/i)).toBeInTheDocument();
  });
});
