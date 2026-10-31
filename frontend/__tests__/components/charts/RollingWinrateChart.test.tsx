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
 * Tests for RollingWinrateChart component.
 *
 * Recharts components are mocked to avoid SVG rendering issues in jsdom.
 * useRollingWinrate hook is mocked to control data state.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RollingWinrateChart } from "@/components/charts/RollingWinrateChart";

// Mock Recharts to avoid SVG/canvas issues in jsdom
jest.mock("recharts", () => {
  const OriginalModule = jest.requireActual("recharts");
  return {
    ...OriginalModule,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
    LineChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
      <div data-testid="line-chart" data-points={data?.length}>{children}</div>
    ),
    Line: () => <div data-testid="line" />,
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

// Mock the hook — we'll override per test
const mockUseRollingWinrate = jest.fn();
jest.mock("@/hooks/useRollingWinrate", () => ({
  useRollingWinrate: (window: number) => mockUseRollingWinrate(window),
}));

const sampleData = [
  { trade_index: 1, closed_at: "2024-01-15T10:00:00Z", rolling_winrate: 0.6, window: 20 },
  { trade_index: 2, closed_at: "2024-01-16T10:00:00Z", rolling_winrate: 0.55, window: 20 },
  { trade_index: 3, closed_at: "2024-01-17T10:00:00Z", rolling_winrate: 0.7, window: 20 },
];

describe("RollingWinrateChart", () => {
  beforeEach(() => {
    mockUseRollingWinrate.mockReset();
  });

  it("shows a spinner when data is loading", () => {
    mockUseRollingWinrate.mockReturnValue({ data: undefined, isLoading: true });
    render(<RollingWinrateChart />);
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
    expect(screen.queryByTestId("line-chart")).not.toBeInTheDocument();
  });

  it("shows empty state message when data is empty array", () => {
    mockUseRollingWinrate.mockReturnValue({ data: [], isLoading: false });
    render(<RollingWinrateChart />);
    expect(
      screen.getByText(/Not enough trades to compute rolling win rate/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId("line-chart")).not.toBeInTheDocument();
  });

  it("renders the chart when data is available", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.queryByTestId("spinner")).not.toBeInTheDocument();
  });

  it("renders the section title", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    expect(screen.getByText(/Rolling Win Rate/i)).toBeInTheDocument();
  });

  it("renders the window selector buttons (10, 20, 50)", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "20" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "50" })).toBeInTheDocument();
  });

  it("defaults to window size 20 (highlighted button)", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    const btn20 = screen.getByRole("button", { name: "20" });
    expect(btn20.className).toContain("bg-primary");
    const btn10 = screen.getByRole("button", { name: "10" });
    expect(btn10.className).not.toContain("bg-primary");
  });

  it("calls useRollingWinrate with default window 20", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    expect(mockUseRollingWinrate).toHaveBeenCalledWith(20);
  });

  it("switches to window 10 when that button is clicked", async () => {
    const user = userEvent.setup();
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    await user.click(screen.getByRole("button", { name: "10" }));
    expect(mockUseRollingWinrate).toHaveBeenCalledWith(10);
    const btn10 = screen.getByRole("button", { name: "10" });
    expect(btn10.className).toContain("bg-primary");
  });

  it("switches to window 50 when that button is clicked", async () => {
    const user = userEvent.setup();
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    await user.click(screen.getByRole("button", { name: "50" }));
    expect(mockUseRollingWinrate).toHaveBeenCalledWith(50);
  });

  it("passes data with correct number of points to LineChart", () => {
    mockUseRollingWinrate.mockReturnValue({ data: sampleData, isLoading: false });
    render(<RollingWinrateChart />);
    const chart = screen.getByTestId("line-chart");
    expect(chart.getAttribute("data-points")).toBe(String(sampleData.length));
  });
});
