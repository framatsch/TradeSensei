import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';


export interface PerformanceDataPoint {
  name: string;
  pnl: number;
  netPnl: number;
  profitFactor: number;
  returnWin: number;
  winPercent: number;
  returnLoss: number;
  returnOthers: number;
  trades: number;
  shares: number;
  mistakes: number;
  avgReturn: number;
  avgNetReturn: number;
  avgProfit: number;
  avgLoser: number;
  commissions: number;
}

interface ResolutionOption {
  label: string;
  value: string;
}

interface PerformanceAnalysisDashboardProps {
  data: PerformanceDataPoint[];
  onViewReport?: (row: PerformanceDataPoint) => void;
  /** Called when a bar in the chart is clicked — receives the same data point as the row. */
  onBarClick?: (row: PerformanceDataPoint) => void;
  /** External label for the current dimension (e.g. 'Hourly', 'Weekday'). Falls back to activeResolution. */
  dimensionLabel?: string;
  /** When provided, renders a segmented control (button group) on the left of the toolbar. */
  resolutions?: ResolutionOption[];
  /** The currently active resolution value — must match one of resolutions[].value. */
  activeResolution?: string;
  /** Called when the user selects a different resolution. */
  onResolutionChange?: (value: string) => void;
}

type MetricType = 'P&L' | 'Trades' | 'Shares' | 'Mistakes' | 'Profit Factor' | 'W vs L';

const formatCurrency = (val: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
const formatPercent = (val: number) => `${val.toFixed(2)}%`;

export const PerformanceAnalysisDashboard: React.FC<PerformanceAnalysisDashboardProps> = ({
  data,
  onViewReport,
  onBarClick,
  dimensionLabel,
  resolutions,
  activeResolution,
  onResolutionChange,
}) => {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('P&L');

  // Effective label: prefer activeResolution when provided, fall back to dimensionLabel
  const effectiveDimensionLabel = activeResolution || dimensionLabel || 'Dimension';

  // Aggregated insights
  const insights = useMemo(() => {
    if (!data.length) return { avgReturn: 0, winRate: 0, totalTrades: 0, totalMistakes: 0, totalPnl: 0 };

    let totalPnl = 0;
    let totalWins = 0;
    let totalTrades = 0;
    let totalMistakes = 0;

    data.forEach(d => {
      totalPnl += d.netPnl;
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
      case 'P&L': return 'netPnl';
      case 'Trades': return 'trades';
      case 'Shares': return 'shares';
      case 'Mistakes': return 'mistakes';
      case 'Profit Factor': return 'profitFactor';
      case 'W vs L': return 'winPercent';
      default: return 'pnl';
    }
  };

  const dataKey = getDataKey(selectedMetric);
  const metrics: MetricType[] = ['P&L', 'Trades', 'Shares', 'Mistakes', 'Profit Factor', 'W vs L'];

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* Consolidated toolbar: resolution segmented control (left) + metric radios (right) */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border/60">
        {/* Left: resolution segmented control — only rendered when resolutions are provided */}
        {resolutions && resolutions.length > 0 && onResolutionChange && (
          <div className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-muted/40 p-1">
            {resolutions.map((res) => (
              <button
                key={res.value}
                onClick={() => onResolutionChange(res.value)}
                className={[
                  "px-3 py-1 rounded-md text-sm font-medium transition-all",
                  activeResolution === res.value
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
                ].join(" ")}
              >
                {res.label}
              </button>
            ))}
          </div>
        )}

        {/* Right: metric selector radio buttons */}
        <div className="flex flex-wrap items-center gap-0.5">
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mr-2">Metric:</span>
          {metrics.map((m) => (
            <label key={m} className="flex items-center space-x-1.5 cursor-pointer group px-1.5 py-1">
              <input
                type="radio"
                name="metric"
                value={m}
                checked={selectedMetric === m}
                onChange={() => setSelectedMetric(m)}
                className="w-3.5 h-3.5 accent-indigo-500"
              />
              <span className={`text-xs ${selectedMetric === m ? 'text-foreground font-medium' : 'text-muted-foreground group-hover:text-foreground'}`}>
                {m}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Middle: Chart & Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Chart Area */}
        <div className="bg-card rounded-xl border border-border overflow-hidden col-span-1 lg:col-span-3 p-4 h-[400px]">
          <h3 className="text-sm font-semibold mb-4 text-foreground">{selectedMetric} by {effectiveDimensionLabel}</h3>
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
                formatter={(value: unknown) => {
                  if (typeof value !== 'number') return [String(value), selectedMetric];
                  if (selectedMetric === 'P&L') return [formatCurrency(value), selectedMetric];
                  if (selectedMetric === 'W vs L') return [formatPercent(value), 'Win Rate'];
                  return [value, selectedMetric];
                }}
              />
              <Bar
                dataKey={dataKey}
                radius={[4, 4, 0, 0]}
                onClick={onBarClick ? (entry) => {
                  if (entry && entry.payload) {
                    onBarClick(entry.payload as PerformanceDataPoint);
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
        <div className="bg-card rounded-xl border border-border overflow-hidden col-span-1 p-6 flex flex-col gap-6">
          <h3 className="text-sm font-semibold text-foreground border-b border-border/50 pb-2">Insights</h3>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Total Net P&L</span>
            <span className={`text-2xl font-bold font-mono ${insights.totalPnl >= 0 ? 'text-success' : 'text-danger'}`}>
              {formatCurrency(insights.totalPnl)}
            </span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Avg Net Return</span>
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
      <div className="bg-card rounded-xl border border-border overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-[#dadbdf] dark:divide-[#29292b]">
          <thead>
            {/* Grouping row */}
            <tr className="bg-muted/20 border-b border-[#dadbdf] dark:border-[#29292b]">
              <th colSpan={3} className="px-4 py-2 text-center text-[10px] font-bold text-zinc-500 uppercase tracking-widest border-r border-[#dadbdf] dark:border-[#29292b]">Overview</th>
              <th colSpan={3} className="px-4 py-2 text-center text-[10px] font-bold text-zinc-500 uppercase tracking-widest border-r border-[#dadbdf] dark:border-[#29292b]">Profit &amp; Loss</th>
              <th colSpan={4} className="px-4 py-2 text-center text-[10px] font-bold text-zinc-500 uppercase tracking-widest border-r border-[#dadbdf] dark:border-[#29292b]">Win/Loss</th>
              <th colSpan={3} className="px-4 py-2 text-center text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Averages</th>
            </tr>
            <tr>
              {/* Overview */}
              <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Name</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Trades</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">Shares</th>
              
              {/* Profit & Loss */}
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-primary uppercase tracking-widest whitespace-nowrap bg-primary/5">Net P&amp;L</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Gross P&amp;L</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">Commissions</th>
              
              {/* Win/Loss */}
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Win %</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Gross Win</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Gross Loss</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">Profit Factor</th>
              
              {/* Averages */}
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-primary uppercase tracking-widest whitespace-nowrap bg-primary/5">Avg Net Return</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Avg Gross Win</th>
              <th scope="col" className="px-4 py-3 text-right text-[10px] font-bold text-zinc-500 uppercase tracking-widest whitespace-nowrap">Avg Gross Loss</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#dadbdf] dark:divide-[#29292b] text-sm">
            {data.map((row, idx) => (
              <tr
                key={idx}
                onClick={() => onViewReport?.(row)}
                className={`transition-colors ${onViewReport ? "cursor-pointer hover:bg-white/[0.05]" : "hover:bg-white/[0.03]"}`}
              >
                {/* Overview */}
                <td className="px-4 py-3 font-medium text-foreground whitespace-nowrap">{row.name}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{row.trades}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">{row.shares.toFixed(2)}</td>
                
                {/* Profit & Loss */}
                <td className={`px-4 py-3 text-right whitespace-nowrap font-medium font-mono bg-primary/5 ${row.netPnl >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(row.netPnl)}
                </td>
                <td className={`px-4 py-3 text-right whitespace-nowrap font-medium font-mono ${row.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(row.pnl)}
                </td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">{formatCurrency(row.commissions)}</td>
                
                {/* Win/Loss */}
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap">{formatPercent(row.winPercent)}</td>
                <td className="px-4 py-3 text-right text-success font-mono whitespace-nowrap">{formatCurrency(row.returnWin)}</td>
                <td className="px-4 py-3 text-right text-danger font-mono whitespace-nowrap">{formatCurrency(row.returnLoss)}</td>
                <td className="px-4 py-3 text-right text-muted-foreground font-mono whitespace-nowrap border-r border-[#dadbdf] dark:border-[#29292b]">{row.profitFactor.toFixed(2)}</td>
                
                {/* Averages */}
                <td className={`px-4 py-3 text-right whitespace-nowrap font-mono bg-primary/5 ${row.avgNetReturn >= 0 ? 'text-success' : 'text-danger'}`}>
                  {formatCurrency(row.avgNetReturn)}
                </td>
                <td className="px-4 py-3 text-right text-success font-mono whitespace-nowrap">{formatCurrency(row.avgProfit)}</td>
                <td className="px-4 py-3 text-right text-danger font-mono whitespace-nowrap">{formatCurrency(row.avgLoser)}</td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={13} className="px-4 py-8 text-center text-muted-foreground">
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
