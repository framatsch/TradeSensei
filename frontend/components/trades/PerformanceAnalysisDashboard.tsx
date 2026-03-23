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
      <div className="flex flex-wrap items-center gap-4 bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
        <span className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Metric:</span>
        <div className="flex flex-wrap items-center gap-4">
          {metrics.map((m) => (
            <label key={m} className="flex items-center space-x-2 cursor-pointer group">
              <input 
                type="radio" 
                name="metric" 
                value={m} 
                checked={selectedMetric === m} 
                onChange={() => setSelectedMetric(m)} 
                className="w-4 h-4 text-indigo-600 bg-gray-100 border-gray-300 focus:ring-indigo-500 dark:focus:ring-indigo-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className={`text-sm ${selectedMetric === m ? 'text-gray-900 dark:text-gray-100 font-medium' : 'text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200'}`}>
                {m}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Middle: Chart & Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Chart Area */}
        <div className="col-span-1 lg:col-span-3 bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 h-[400px]">
          <h3 className="text-lg font-semibold mb-4 text-gray-800 dark:text-gray-100">{selectedMetric} by {dimensionLabel || 'Dimension'}</h3>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
              <XAxis dataKey="name" tick={{ fill: '#6B7280', fontSize: 12 }} tickMargin={10} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
              <YAxis tick={{ fill: '#6B7280', fontSize: 12 }} tickFormatter={(val) => selectedMetric === 'P&L' ? `$${val}` : val} axisLine={false} tickLine={false} />
              <Tooltip 
                cursor={{ fill: 'rgba(0,0,0,0.05)' }} 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
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
                    fill = isPositive ? '#10B981' : '#EF4444'; // Emerald/Red
                  } else if (selectedMetric === 'Mistakes') {
                    fill = val > 0 ? '#F59E0B' : '#10B981'; // Amber/Emerald
                  }
                  
                  return <Cell key={`cell-${index}`} fill={fill} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Insights Sidebar */}
        <div className="col-span-1 bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col gap-6">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 border-b pb-2 dark:border-gray-700">Insights</h3>
          
          <div className="flex flex-col gap-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">Total P&L</span>
            <span className={`text-2xl font-bold ${insights.totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatCurrency(insights.totalPnl)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">Avg Return</span>
            <span className={`text-xl font-semibold ${insights.avgReturn >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatCurrency(insights.avgReturn)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">Win Rate</span>
            <span className="text-xl font-semibold text-gray-800 dark:text-gray-100">
              {formatPercent(insights.winRate)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-sm text-gray-500 dark:text-gray-400">Total Trades</span>
            <span className="text-xl font-semibold text-gray-800 dark:text-gray-100">
              {insights.totalTrades}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom: Data Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900/50">
            <tr>
              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Name</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Return $</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Profit Factor</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Return Win</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Win %</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Return Loss</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Return Others</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Trades</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Shares</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Avg Return</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Avg Profit</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Avg Loser</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">Commissions/Fees</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap"></th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700 text-sm">
            {data.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">{row.name}</td>
                <td className={`px-4 py-3 text-right whitespace-nowrap font-medium ${row.pnl >= 0 ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}`}>
                  {formatCurrency(row.pnl)}
                </td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{row.profitFactor.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-green-600 dark:text-green-500 whitespace-nowrap">{formatCurrency(row.returnWin)}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{formatPercent(row.winPercent)}</td>
                <td className="px-4 py-3 text-right text-red-600 dark:text-red-500 whitespace-nowrap">{formatCurrency(row.returnLoss)}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{formatCurrency(row.returnOthers)}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{row.trades}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{row.shares}</td>
                <td className={`px-4 py-3 text-right whitespace-nowrap ${row.avgReturn >= 0 ? 'text-green-600 dark:text-green-500' : 'text-red-600 dark:text-red-500'}`}>
                  {formatCurrency(row.avgReturn)}
                </td>
                <td className="px-4 py-3 text-right text-green-600 dark:text-green-500 whitespace-nowrap">{formatCurrency(row.avgProfit)}</td>
                <td className="px-4 py-3 text-right text-red-600 dark:text-red-500 whitespace-nowrap">{formatCurrency(row.avgLoser)}</td>
                <td className="px-4 py-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">{formatCurrency(row.commissions)}</td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <button 
                    onClick={() => onViewReport?.(row)}
                    className="inline-flex items-center text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium transition-colors"
                  >
                    View Report <ChevronRight className="w-4 h-4 ml-1" />
                  </button>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={14} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
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
