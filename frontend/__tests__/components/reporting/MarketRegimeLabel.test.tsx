import React from 'react';
import { render, screen } from '@testing-library/react';
import { PsychologicalAttributionWidget, PlaybookPhaseHeatmapWidget } from '@/components/reporting/Widgets';

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
  const attributionData = {
    total_trades: 3,
    buckets: [
      { phase: 'Bull', playbook: 'PB1', trade_count: 3, win_rate: 0.5, avg_pnl: '100' }
    ]
  };

  test('PsychologicalAttributionWidget renders "Market Regime" instead of "Market Phase"', () => {
    const { container } = render(
      <PsychologicalAttributionWidget 
        data={attributionData as any} 
        isLoading={false} 
        
      />
    );
    
    expect(screen.getAllByText(/Market Regime/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Market Phase/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Market Phase/i);
  });

  test('PlaybookPhaseHeatmapWidget renders "Market Regime" instead of "Market Phase"', () => {
    const { container } = render(
      <PlaybookPhaseHeatmapWidget 
        data={attributionData as any} 
        isLoading={false} 
        
      />
    );
    
    expect(screen.getAllByText(/Market Regime/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Market Phase/i)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/Market Phase/i);
  });
});
