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
import { MaeMfeScatterWidget, DurationVsPnlScatterWidget } from '@/components/reporting/Widgets';

// Mock Recharts to avoid DOM measurement issues in Jest
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ScatterChart: () => <div data-testid="scatter-chart">ScatterChart</div>,
  Scatter: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ZAxis: () => null,
  ReferenceLine: () => null,
}));

describe('Scatter Circuit Breaker', () => {
  const generateData = (count: number) => {
    return Array.from({ length: count }).map((_, i) => ({
      x: i,
      y: i,
      count: 1,
      label: 'test'
    }));
  };

  describe('MaeMfeScatterWidget', () => {
    test('renders ScatterChart when data.length <= 500', () => {
      const data = generateData(500);
      render(<MaeMfeScatterWidget data={data} isLoading={false} />);
      expect(screen.getByTestId('scatter-chart')).toBeInTheDocument();
      expect(screen.queryByText(/Too many points/)).not.toBeInTheDocument();
    });

    test('renders fallback UI and NOT ScatterChart when data.length > 500', () => {
      const data = generateData(501);
      render(<MaeMfeScatterWidget data={data} isLoading={false} />);
      expect(screen.queryByTestId('scatter-chart')).not.toBeInTheDocument();
      expect(screen.getByText(/Too many points \(501\)/)).toBeInTheDocument();
    });
  });

  describe('DurationVsPnlScatterWidget', () => {
    test('renders ScatterChart when data.length <= 500', () => {
      const data = generateData(500);
      render(<DurationVsPnlScatterWidget data={data} isLoading={false} />);
      expect(screen.getByTestId('scatter-chart')).toBeInTheDocument();
      expect(screen.queryByText(/Too many points/)).not.toBeInTheDocument();
    });

    test('renders fallback UI and NOT ScatterChart when data.length > 500', () => {
      const data = generateData(501);
      render(<DurationVsPnlScatterWidget data={data} isLoading={false} />);
      expect(screen.queryByTestId('scatter-chart')).not.toBeInTheDocument();
      expect(screen.getByText(/Too many points \(501\)/)).toBeInTheDocument();
    });
  });
});
