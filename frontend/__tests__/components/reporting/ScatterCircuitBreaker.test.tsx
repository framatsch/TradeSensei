import React from 'react';
import { render, screen } from '@testing-library/react';
import { MaeMfeScatterWidget, DurationVsPnlScatterWidget } from '@/components/reporting/Widgets';

// Mock Recharts to avoid DOM measurement issues in Jest
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
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
