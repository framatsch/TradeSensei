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

import React from 'react';
import { render, screen } from '@testing-library/react';
import { PlaybookPhaseHeatmapWidget, UncategorizedBanner } from '@/components/reporting/Widgets';

// Mock Recharts
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: () => <div>BarChart</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}));

describe('Market Regime Label', () => {
  test('PlaybookPhaseHeatmapWidget renders "Market Regime" instead of "Market Phase"', () => {
    const { container } = render(
      <PlaybookPhaseHeatmapWidget 
        data={[]} 
        isLoading={false} 
      />
    );
    
    expect(screen.getAllByText(/Market Regime/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Market Phase/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Market Phase/i);
  });

  test('UncategorizedBanner renders "market regime"', () => {
    render(<UncategorizedBanner unmatchedCount={0} phaseUnsetCount={1} />);
    expect(screen.getByText(/market regime/i)).toBeInTheDocument();
    expect(screen.queryByText(/market phase/i)).not.toBeInTheDocument();
  });
});
