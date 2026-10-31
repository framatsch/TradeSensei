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

"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ArrowDown, ArrowLeft, ArrowUp, MoreHorizontal, Split } from "lucide-react";
import type { Trade } from "@/lib/types";
import { formatSplitRatio } from "@/lib/formatSplitRatio";

interface Props {
  trade: Trade;
  realizedR: number | null;
  returnPct: number | null;
  holdingPeriod: string;
  onCorrectTrade: () => void;
  onMerge: () => void;
  backHref?: string;
  navigationControls?: ReactNode;
  positionIndicator?: ReactNode;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function TradeMobileHeader({
  trade,
  realizedR,
  returnPct,
  holdingPeriod,
  onCorrectTrade,
  onMerge,
  backHref = "/dashboard/trades",
  navigationControls,
  positionIndicator,
}: Props) {
  const isLong = trade.direction === "LONG";
  const pnl = trade.pnl === null ? null : Number(trade.pnl);
  const kpis = [
    { label: "P&L", value: pnl, prefix: "$", suffix: "" },
    { label: "Realized R", value: realizedR, prefix: "", suffix: "R" },
    { label: "Return %", value: returnPct, prefix: "", suffix: "%" },
  ];

  return (
    <header className="solid-card p-4 shadow-sm lg:hidden">
      <div className="flex min-w-0 items-center gap-1.5">
        <Link
          href={backHref}
          aria-label="Back to Trades"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft size={18} aria-hidden="true" />
        </Link>
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <h1 className="truncate text-xl font-bold text-foreground" title={trade.symbol}>{trade.symbol}</h1>
          {!!trade.corporate_action_impact?.length && (
            <span
              className="shrink-0 text-muted-foreground"
              tabIndex={0}
              aria-label="Affected by a corporate action"
              title={trade.corporate_action_impact.map((action) => `Split ${formatSplitRatio(action.ratio)} on ${action.date}`).join("\n")}
            >
              <Split size={16} aria-hidden="true" />
            </span>
          )}
        </div>
        {navigationControls}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              type="button"
              aria-label="Trade actions"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <MoreHorizontal size={18} aria-hidden="true" />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content align="end" sideOffset={4} className="z-50 w-44 rounded-lg border border-border bg-popover py-1 shadow-lg">
              <DropdownMenu.Item onSelect={onCorrectTrade} className="cursor-pointer px-3 py-2.5 text-sm text-foreground outline-none data-[highlighted]:bg-secondary">
                Correct Trade…
              </DropdownMenu.Item>
              <DropdownMenu.Item onSelect={onMerge} className="cursor-pointer px-3 py-2.5 text-sm text-foreground outline-none data-[highlighted]:bg-secondary">
                Merge with…
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold">
        {trade.direction && !trade.is_combo && (
          <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 ${isLong ? "border-[color-mix(in_srgb,var(--success)_30%,transparent)] bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-success" : "border-[color-mix(in_srgb,var(--danger)_30%,transparent)] bg-[color-mix(in_srgb,var(--danger)_15%,transparent)] text-danger"}`}>
            {isLong ? <ArrowUp size={10} aria-hidden="true" /> : <ArrowDown size={10} aria-hidden="true" />}
            {trade.direction}
          </span>
        )}
        <span className="rounded border border-border bg-secondary px-2 py-0.5 text-muted-foreground">{trade.is_combo ? "COMBO" : trade.asset_class}</span>
        <span className={`rounded border px-2 py-0.5 ${trade.closed_at ? "border-border bg-secondary text-muted-foreground" : "border-[color-mix(in_srgb,var(--warning)_30%,transparent)] bg-[color-mix(in_srgb,var(--warning)_15%,transparent)] text-warning"}`}>
          {trade.closed_at ? "Closed" : "Open"}
        </span>
        {trade.is_manually_edited && <span className="rounded border border-border bg-secondary px-2 py-0.5 text-primary">Manually Edited</span>}
      </div>

      <p className="mt-2 truncate font-mono text-[10px] text-muted-foreground sm:text-xs" title={`${formatDate(trade.opened_at)} → ${formatDate(trade.closed_at)} · ${holdingPeriod}`}>
        {formatDate(trade.opened_at)} → {formatDate(trade.closed_at)} · {holdingPeriod}
      </p>
      {positionIndicator && <div className="mt-1 flex justify-end font-mono text-xs text-muted-foreground">{positionIndicator}</div>}

      <dl className="mt-3 grid grid-cols-3 divide-x divide-border rounded-lg border border-border bg-secondary py-3">
        {kpis.map(({ label, value, prefix, suffix }) => (
          <div key={label} className="min-w-0 px-1 text-center">
            <dd className={`font-mono text-sm font-semibold ${value === null || !Number.isFinite(value) ? "text-muted-foreground" : value >= 0 ? "text-success" : "text-danger"}`}>
              {value === null || !Number.isFinite(value) ? "—" : `${value >= 0 ? "+" : "-"}${prefix}${Math.abs(value).toFixed(2)}${suffix}`}
            </dd>
            <dt className="mt-1 text-[10px] text-muted-foreground">{label}</dt>
          </div>
        ))}
      </dl>
    </header>
  );
}
