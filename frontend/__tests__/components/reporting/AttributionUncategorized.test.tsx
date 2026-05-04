import React from 'react';
import { render, screen } from '@testing-library/react';
import { PsychologicalAttributionWidget, PlaybookPhaseHeatmapWidget } from '@/components/reporting/Widgets';

// Mock Recharts
jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: () => <div data-testid="bar-chart">BarChart</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
}));

describe('Attribution Uncategorized', () => {
  describe('PsychologicalAttributionWidget', () => {
    test('renders "Uncategorized" bar when input data contains entries with no check-in id', () => {
      const attributionData = {
        total_trades: 10,
        buckets: [
          { phase: 'Bull', playbook: 'PB1', trade_count: 3, win_rate: 0.5, avg_pnl: '100' }
        ]
      };
      
      // Pass total_trades = 10, but buckets only sum to 3. Uncategorized = 7.
      render(
        <PsychologicalAttributionWidget 
          data={attributionData as any} 
          isLoading={false} 
          
        />
      );
      
      // In the table view which renders alongside the chart
      expect(screen.getByText('Uncategorized')).toBeInTheDocument();
    });

    test('Uncategorized bar is absent when all entries have a check-in id', () => {
      const attributionData = {
        total_trades: 3,
        buckets: [
          { phase: 'Bull', playbook: 'PB1', trade_count: 3, win_rate: 0.5, avg_pnl: '100' }
        ]
      };
      
      // total_trades matches sum of buckets.
      render(
        <PsychologicalAttributionWidget 
          data={attributionData as any} 
          isLoading={false} 
          
        />
      );
      
      expect(screen.queryByText('Uncategorized')).not.toBeInTheDocument();
    });
  });

  describe('PlaybookPhaseHeatmapWidget', () => {
    test('renders "Uncategorized" row when input data contains entries with no check-in id', () => {
      const attributionData = {
        total_trades: 10,
        buckets: [
          { phase: 'Bull', playbook: 'PB1', trade_count: 3, win_rate: 0.5, avg_pnl: '100' }
        ]
      };
      
      render(
        <PlaybookPhaseHeatmapWidget 
          data={attributionData as any} 
          isLoading={false} 
          
        />
      );
      
      expect(screen.getByText('Uncategorized')).toBeInTheDocument();
    });
  });
});
