/**
 * DashboardStats — 4-tile bento grid of key trading metrics.
 *
 * Tiles: Avg RRR, Gross Profit, Gross Loss, Sharpe Ratio.
 * Win Rate and Profit Factor are already visible in the DashboardHeader hero section.
 */

"use client";

import {
  TrendingUp,
  TrendingDown,
  Activity,
  Minus,
} from "lucide-react";
import type { MetricsSummary } from "@/lib/types";
import { MetricHelpLink } from "@/components/ui/MetricHelpLink";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(value: string | null, decimals = 2): string {
  if (!value) return "—";
  return parseFloat(value).toFixed(decimals);
}

function fmtCurrency(value: string | null): string {
  if (!value) return "—";
  const num = parseFloat(value);
  const abs = Math.abs(num);
  const prefix = num >= 0 ? "+" : "−";
  if (abs >= 1_000_000) return `${prefix}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${prefix}$${(abs / 1_000).toFixed(2)}K`;
  return `${prefix}$${abs.toFixed(2)}`;
}

// ─── StatTile ─────────────────────────────────────────────────────────────────

interface StatTileProps {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  accentClass?: string;
  helpAnchor?: string;
}

function StatTile({
  label,
  value,
  sub,
  icon,
  accentClass = "text-muted-foreground",
  helpAnchor,
}: StatTileProps) {
  return (
    <div className="radiant-card light-edge noise-overlay p-5 flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-1.5">
          {label}
          {helpAnchor && <MetricHelpLink anchor={helpAnchor} />}
        </span>
        <span className={`${accentClass} opacity-70`}>{icon}</span>
      </div>

      {/* Main value */}
      <p
        className={`text-3xl font-bold tracking-tight font-mono leading-none ${accentClass}`}
      >
        {value}
      </p>

      {/* Sub-label */}
      {sub && (
        <p className="text-xs text-muted-foreground font-mono">{sub}</p>
      )}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface Props {
  summary: MetricsSummary;
}

export function DashboardStats({ summary }: Props) {
  const m = summary.metrics;

  const sharpe = m.sharpe_ratio ? parseFloat(m.sharpe_ratio) : null;

  // Avg RRR = avg_win / |avg_loss|
  const avgWin = parseFloat(m.avg_win);
  const avgLoss = Math.abs(parseFloat(m.avg_loss));
  const rrr = avgLoss > 0 ? avgWin / avgLoss : null;

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
      {/* Avg RRR */}
      <StatTile
        label="Avg RRR"
        value={rrr !== null ? `${rrr.toFixed(2)}R` : "—"}
        sub={rrr !== null ? `Win $${avgWin.toFixed(2)} · Loss $${avgLoss.toFixed(2)}` : undefined}
        icon={<Activity size={16} />}
        accentClass={rrr !== null && rrr >= 1 ? "text-success" : "text-foreground"}
        helpAnchor="avg-rrr"
      />

      {/* Gross Profit */}
      <StatTile
        label="Gross Profit"
        value={fmtCurrency(m.gross_profit)}
        sub={`${m.winning_trades} winning trades`}
        icon={<TrendingUp size={16} />}
        accentClass="text-success"
        helpAnchor="gross-profit"
      />

      {/* Gross Loss */}
      <StatTile
        label="Gross Loss"
        value={fmtCurrency(m.gross_loss)}
        sub={`${m.losing_trades} losing trades`}
        icon={<TrendingDown size={16} />}
        accentClass="text-danger"
        helpAnchor="gross-loss"
      />

      {/* Sharpe Ratio */}
      <StatTile
        label="Sharpe Ratio"
        value={sharpe !== null ? fmt(m.sharpe_ratio, 2) : "—"}
        sub={
          sharpe !== null
            ? sharpe >= 2
              ? "Excellent"
              : sharpe >= 1
              ? "Good"
              : sharpe >= 0
              ? "Below average"
              : "Poor"
            : "Insufficient data"
        }
        icon={<Minus size={16} />}
        accentClass={
          sharpe !== null
            ? sharpe >= 1
              ? "text-success"
              : sharpe >= 0
              ? "text-foreground"
              : "text-danger"
            : "text-muted-foreground"
        }
        helpAnchor="sharpe-ratio"
      />
    </div>
  );
}
