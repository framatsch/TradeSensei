import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { ChevronRight } from 'lucide-react';

export interface PerformanceDataPoint {
  name: string;
  pnl: number;
  profitFactor: number;
  returnWin: number;
  winPercent: number;
  returnLoss: number;
  returnOthers: number;
  trades: number;
  shares: number;
  mistakes: number;
  avgReturn: number;
  avgProfit: number;
  avgLoser: number;
  commissions: number;
}

interface PerformanceAnalysisDashboardProps {
  data: PerformanceDataPoint[];
  onViewReport?: (row: PerformanceDataPoint) => void;
  /** Called when a bar in the chart is clicked — receives the same data point as the row. */
  onBarClick?: (row: PerformanceDataPoint) => void;
  // External control of current dimension for label (e.g. 'Hourly', 'Weekday', 'Monthly', 'Yearly')
  dimensionLabel?: string;
}

type MetricType = 'P&L' | 'Trades' | 'Shares' | 'Mistakes' | 'Profit Factor' | 'W vs L';

const formatCurrency = (val: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
const formatPercent = (val: number) => `${val.toFixed(2)}%`;

export const PerformanceAnalysisDashboard: React.FC<PerformanceAnalysisDashboardProps> = ({ data, onViewReport, onBarClick, dimensionLabel }) => {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('P&L');

  // Aggregated insights
  const insights = useMemo(() => {
    if (!data.length) return { avgReturn: 0, winRate: 0, totalTrades: 0, totalMistakes: 0, totalPnl: 0 };
    
    let totalPnl = 0;
    let totalWins = 0;
    let totalTrades = 0;
    let totalMistakes = 0;

    data.forEach(d => {
      totalPnl += d.pnl;
      totalTrades += d.trades;
      totalMistakes += d.mistakes || 0;
      totalWins += (d.winPercent / 100) * d.trades;
    });

    const avgReturn = totalTrades > 0 ? totalPnl / totalTrades : 0;
    const winRate = totalTrades > 0 ? (totalWins / totalTrades) * 100 : 0;

    return {
      avgReturn,
      winRate,
      totalTrades,
      totalMistakes,
      totalPnl
    };
  }, [data]);

  // Determine which key to plot
  const getDataKey = (metric: MetricType) => {
    switch (metric) {
      case 'P&L': return 'pnl';
      case 'Trades': return 'trades';
      case 'Shares': return 'shares';
      case 'Mistakes': return 'mistakes';
      case 'Profit Factor': return 'profitFactor';
      case 'W vs L': return 'winPercent'; // Using win percent as proxy for W vs L in a simple bar chart
      default: return 'pnl';
    }
  };

  const dataKey = getDataKey(selectedMetric);

  const metrics: MetricType[] = ['P&L', 'Trades', 'Shares', 'Mistakes', 'Profit Factor', 'W vs L'];

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Top: Filter Bar */}
      <div className="radiant-card flex flex-wrap items-center gap-4 p-4">
        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Metric:</span>
        <div className="flex flex-wrap items-center gap-4">
          {metrics.map((m) => (
            <label key={m} className="flex items-center space-x-2 cursor-pointer group">
              <input 
                type="radio" 
                name="metric" 
                value={m} 
                checked={selectedMetric === m} 
                onChange={() => setSelectedMetric(m)} 
                className="w-4 h-4 accent-indigo-500"
              />
              <span className={`text-sm ${selectedMetric === m ? 'text-foreground font-medium' : 'text-muted-foreground group-hover:text-foreground'}`}>
                {m}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Middle: Chart & Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Chart Area */}
        <div className="radiant-card col-span-1 lg:col-span-3 p-4 h-[400px]">
          <h3 className="text-sm font-semibold mb-4 text-foreground">{selectedMetric} by {dimensionLabel || 'Dimension'}</h3>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 12 }} tickMargin={10} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickLine={false} />
              <YAxis tick={{ fill: '#71717a', fontSize: 12 }} tickFormatter={(val) => selectedMetric === 'P&L' ? `$${val}` : val} axisLine={false} tickLine={false} />
              <Tooltip 
                cursor={{ fill: 'rgba(255,255,255,0.03)' }} 
                contentStyle={{ background: 'var(--popover)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}
                labelStyle={{ color: 'var(--foreground)' }}
                itemStyle={{ color: 'var(--foreground)' }}
                formatter={(value: any) => {
                  if (typeof value !== 'number') return [value, selectedMetric];
                  if (selectedMetric === 'P&L') return [formatCurrency(value), selectedMetric];
                  if (selectedMetric === 'W vs L') return [formatPercent(value), 'Win Rate'];
                  return [value, selectedMetric];
                }}
              />
              <Bar
                dataKey={dataKey}
                radius={[4, 4, 0, 0]}
                onClick={onBarClick ? (data) => {
                  if (data && data.payload) {
                    onBarClick(data.payload as PerformanceDataPoint);
                  }
                } : undefined}
                cursor={onBarClick ? "pointer" : undefined}
              >
                {data.map((entry, index) => {
                  const val = entry[dataKey as keyof PerformanceDataPoint] as number;
                  const isPositive = val >= 0;
                  
                  let fill = '#6366F1'; // Default Indigo
                  if (selectedMetric === 'P&L' || selectedMetric === 'Profit Factor') {
                    fill = isPositive ? '#34d399' : '#fb7185'; // Emerald/Rose
                  } else if (selectedMetric === 'Mistakes') {
                    fill = val > 0 ? '#F59E0B' : '#34d399'; // Amber/Emerald
                  }
                  
                  return <Cell key={`cell-${index}`} fill={fill} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Insights Sidebar */}
        <div className="radiant-card col-span-1 p-6 flex flex-col gap-6">
          <h3 className="text-sm font-semibold text-foreground border-b border-border/50 pb-2">Insights</h3>
          
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Total P&L</span>
            <span className={`text-2xl font-bold font-mono ${insights.totalPnl >= 0 ? 'text-success' : 'text-danger'}`}>
              {formatCurrency(insights.totalPnl)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Avg Return</span>
            <span className={`text-xl font-semibold font-mono ${insights.avgReturn >= 0 ? 'text-success' : 'text-danger'}`}>
              {formatCurrency(insights.avgReturn)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Win Rate</span>
            <span className="text-xl font-semibold font-mono text-foreground">
              {formatPercent(insights.winRate)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Total Trades</span>
            <span className="text-xl font-semibold font-mono text-foreground">
              {insights.totalTrades}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom: Data Table */}
      <div className="radiant-card overflow-x-auto">
        <table className="min-w-full divide-y divide-zinc-900">
          <thead>
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Name</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Return $</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Profit Factor</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Return Win</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Win %</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Return Loss</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Return Others</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Trades</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Shares</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Avg Return</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Avg Profit</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Avg Loser</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Commissions/Fees</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-900 text-sm">
            {data.map((row, idx) => (
              <tr key={idx} className="hover:bg-white/[0.03] transition-colors">
                <td className="px-4 py-3 font-medium text-foreground whitespace-nowrap">{row.name}</td>
                <td className={`px-4 py-3 text-right whitespace-nowrap font-medium font-mono ${row.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(row.pnl)}
                </td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{row.profitFactor.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-success font-mono whitespace-nowrap">{formatCurrency(row.returnWin)}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{formatPercent(row.winPercent)}</td>
                <td className="px-4 py-3 text-right text-danger font-mono whitespace-nowrap">{formatCurrency(row.returnLoss)}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{formatCurrency(row.returnOthers)}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{row.trades}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{row.shares}</td>
                <td className={`px-4 py-3 text-right whitespace-nowrap font-mono ${row.avgReturn >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(row.avgReturn)}
                </td>
                <td className="px-4 py-3 text-right text-success font-mono whitespace-nowrap">{formatCurrency(row.avgProfit)}</td>
                <td className="px-4 py-3 text-right text-danger font-mono whitespace-nowrap">{formatCurrency(row.avgLoser)}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{formatCurrency(row.commissions)}</td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <button 
                    onClick={() => onViewReport?.(row)}
                    className="inline-flex items-center text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                  >
                    View Report <ChevronRight className="w-4 h-4 ml-1" />
                  </button>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={14} className="px-4 py-8 text-center text-muted-foreground">
                  No performance data available for the selected view.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
