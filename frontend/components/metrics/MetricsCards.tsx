/**
 * MetricsCards — summary stat cards for dashboard overview.
 */

import type { TradeMetrics } from "@/lib/types";

interface Props {
  metrics: TradeMetrics;
  maxDrawdown: string;
}

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  positive?: boolean | null;
}

function StatCard({ label, value, sub, positive }: StatCardProps) {
  const valueColor =
    positive === null || positive === undefined
      ? "text-foreground"
      : positive
        ? "text-emerald-500 dark:text-emerald-400"
        : "text-rose-500 dark:text-rose-400";

  return (
    <div className="bg-card rounded-xl p-5 border border-border shadow-sm hover:shadow-md transition-shadow">
      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-1">
        {label}
      </p>
      <p className={`text-2xl font-semibold tracking-tight ${valueColor}`}>{value}</p>
      {sub && <p className="text-[11px] text-muted-foreground mt-1.5 font-medium">{sub}</p>}
    </div>
  );
}

function formatPercent(value: string | null): string {
  if (value === null) return "—";
  const num = parseFloat(value);
  return `${(num * 100).toFixed(1)}%`;
}

function formatPnl(value: string): string {
  const num = parseFloat(value);
  const prefix = num >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(num).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDecimal(value: string | null, decimals = 2): string {
  if (value === null) return "—";
  return parseFloat(value).toFixed(decimals);
}

export function MetricsCards({ metrics, maxDrawdown }: Props) {
  const totalPnlNum = parseFloat(metrics.total_pnl);
  const maxDdNum = parseFloat(maxDrawdown);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
      <StatCard
        label="Total Trades"
        value={metrics.total_trades.toString()}
        sub={`${metrics.winning_trades}W / ${metrics.losing_trades}L`}
      />
      <StatCard
        label="Win Rate"
        value={formatPercent(metrics.win_rate)}
        positive={parseFloat(metrics.win_rate) >= 0.5}
      />
      <StatCard
        label="Total PnL"
        value={formatPnl(metrics.total_pnl)}
        positive={totalPnlNum >= 0}
      />
      <StatCard
        label="Profit Factor"
        value={formatDecimal(metrics.profit_factor)}
        sub={metrics.profit_factor ? "gross profit / gross loss" : undefined}
        positive={
          metrics.profit_factor
            ? parseFloat(metrics.profit_factor) >= 1
            : null
        }
      />
      <StatCard
        label="Sharpe Ratio"
        value={formatDecimal(metrics.sharpe_ratio)}
        sub="annualised"
        positive={
          metrics.sharpe_ratio ? parseFloat(metrics.sharpe_ratio) >= 1 : null
        }
      />
      <StatCard
        label="Max Drawdown"
        value={formatPercent(maxDrawdown)}
        sub={`$${Math.abs(parseFloat(metrics.gross_loss)).toFixed(2)} gross loss`}
        positive={maxDdNum >= -0.1}
      />
    </div>
  );
}
