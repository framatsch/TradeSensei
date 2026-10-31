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

  it("renders the preset selector and emits a from_date-compatible custom value for IBKR", () => {
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

    expect(screen.getByRole("combobox")).toHaveValue("ytd");
    expect(screen.getByRole("option", { name: "Year to date" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "custom" } });
    expect(onPresetChange).toHaveBeenCalledWith("custom");
    expect(onCustomFromDateChange).toHaveBeenCalledWith("20260101");
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

    expect(screen.getByRole("combobox")).toHaveValue("ytd");
    expect(screen.getByRole("option", { name: "Year to date" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Custom date..." })).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-01-01")).toBeInTheDocument();
    expect(screen.getByText(/Broker API limit: 365 days/i)).toBeInTheDocument();
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

    const dateInput = screen.getByDisplayValue("2025-07-18");
    expect(dateInput).toHaveAttribute("min", "2025-07-18");
    expect(dateInput).toHaveAttribute("max", "2026-07-18");
    expect(screen.getByText(/Selected: 365 days/i)).toBeInTheDocument();
    expect(screen.getByText(/Broker API limit: 365 days/i)).toBeInTheDocument();

    fireEvent.change(dateInput, { target: { value: "2026-06-15" } });
    expect(onPresetChange).toHaveBeenCalledWith("custom");
    expect(onCustomFromDateChange).toHaveBeenCalledWith("20260615");
  });
});
