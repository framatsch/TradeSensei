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
