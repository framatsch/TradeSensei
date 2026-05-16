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
 * Tests for MonthlyWinrateChart component.
 *
 * Recharts components are mocked to avoid SVG rendering issues in jsdom.
 * useMonthlyWinrate hook is mocked to control data state.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { MonthlyWinrateChart } from "@/components/charts/MonthlyWinrateChart";

// Mock Recharts
jest.mock("recharts", () => {
  const OriginalModule = jest.requireActual("recharts");
  return {
    ...OriginalModule,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    BarChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
      <div data-testid="bar-chart" data-points={data?.length}>{children}</div>
    ),
    Bar: ({ dataKey }: { dataKey: string }) => (
      <div data-testid="bar" data-key={dataKey} />
    ),
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    ReferenceLine: () => null,
  };
});

// Mock Spinner
jest.mock("@/components/ui/Spinner", () => ({
  Spinner: () => <div data-testid="spinner" />,
}));

// Mock the hook
const mockUseMonthlyWinrate = jest.fn();
jest.mock("@/hooks/useMonthlyWinrate", () => ({
  useMonthlyWinrate: () => mockUseMonthlyWinrate(),
}));

const sampleData = [
  {
    year: 2024,
    month: 1,
    label: "Jan 2024",
    win_rate: "0.6",
    win_count: 6,
    loss_count: 4,
    trade_count: 10,
  },
  {
    year: 2024,
    month: 2,
    label: "Feb 2024",
    win_rate: "0.4",
    win_count: 4,
    loss_count: 6,
    trade_count: 10,
  },
  {
    year: 2024,
    month: 3,
    label: "Mar 2024",
    win_rate: "0.75",
    win_count: 9,
    loss_count: 3,
    trade_count: 12,
  },
];

describe("MonthlyWinrateChart", () => {
  beforeEach(() => {
    mockUseMonthlyWinrate.mockReset();
  });

  it("shows a spinner when data is loading", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: undefined, isLoading: true });
    render(<MonthlyWinrateChart />);
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
  });

  it("shows empty state message when data is empty array", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: [], isLoading: false });
    render(<MonthlyWinrateChart />);
    expect(
      screen.getByText(/No monthly win rate data available/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
  });

  it("renders the chart when data is available", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<MonthlyWinrateChart />);
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("renders the section title", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<MonthlyWinrateChart />);
    expect(screen.getByText(/Monthly Win Rate/i)).toBeInTheDocument();
  });

  it("passes data with correct number of points to BarChart", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<MonthlyWinrateChart />);
    const chart = screen.getByTestId("bar-chart");
    expect(chart.getAttribute("data-points")).toBe(String(sampleData.length));
  });

  it("renders a Bar with dataKey=win_rate", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<MonthlyWinrateChart />);
    const bar = screen.getByTestId("bar");
    expect(bar.getAttribute("data-key")).toBe("win_rate");
  });

  it("shows empty state when data is null/undefined", () => {
    mockUseMonthlyWinrate.mockReturnValue({ data: null, isLoading: false });
    render(<MonthlyWinrateChart />);
    expect(
      screen.getByText(/No monthly win rate data available/i)
    ).toBeInTheDocument();
  });
});
