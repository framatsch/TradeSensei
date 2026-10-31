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

/**
 * useReportData — centralized hook for reports pages.
 *
 * Fetches all trades (up to 5000) and provides:
 *  - raw trades list
 *  - aggregatedData(dimension) — PerformanceDataPoint[] for the analysis table
 *  - calendarData — DailyTradeData[] for the calendar component
 *  - loading / error states
 */
"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import type { Trade, CursorPage, ResponseEnvelope } from "@/lib/types";
import type { PerformanceDataPoint } from "@/components/analytics/PerformanceAnalysisDashboard";
import type { DailyTradeData } from "@/components/calendar/types";

import type { DashboardFilterConfig } from "@/lib/api/types.gen";

export type ReportDimension = "Hourly" | "Weekday" | "Monthly" | "Yearly";

function buildKey(date: Date, dimension: ReportDimension): string {
  switch (dimension) {
    case "Hourly":
      return date.getHours().toString().padStart(2, "0") + ":00";
    case "Weekday": {
      const days = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
      ];
      return days[date.getDay()];
    }
    case "Monthly": {
      const months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ];
      return months[date.getMonth()];
    }
    case "Yearly":
      return date.getFullYear().toString();
  }
}

function sortResult(
  result: PerformanceDataPoint[],
  dimension: ReportDimension,
): PerformanceDataPoint[] {
  if (dimension === "Hourly") {
    return result.sort((a, b) => a.name.localeCompare(b.name));
  }
  if (dimension === "Weekday") {
    const order = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    return result.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
  }
  if (dimension === "Monthly") {
    const order = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return result.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
  }
  return result.sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Fetch all trades by walking the cursor-pagination (API hard-limit is 100
 * per page). Accumulates every page and returns the full list.
 */
async function fetchAllTrades(
  portfolioId?: string,
  signal?: AbortSignal,
): Promise<Trade[]> {
  const PAGE_SIZE = 100;
  const allItems: Trade[] = [];
  let cursor: string | null = null;

  do {
    const query: Record<string, string | number> = { limit: PAGE_SIZE };
    if (cursor) query.cursor = cursor;

    const url = portfolioId
      ? `/api/v1/portfolios/${portfolioId}/trades`
      : "/api/v1/trades";
    const { data, error } = await client.get<{
      200: ResponseEnvelope<CursorPage<Trade>> | CursorPage<Trade>;
    }>({ url, query, signal });
    if (error || !data) throw error ?? new Error("Request failed: no data returned");
    const pageData = "data" in data ? data.data : data;
    allItems.push(...pageData.items);
    cursor = pageData.next_cursor ?? null;
  } while (cursor !== null);

  return allItems;
}

export function useReportData(
  portfolioIdParam?: string | null,
  filterConfig?: DashboardFilterConfig | null,
) {
  const storePortfolioId = usePortfolioStore(
    (state) => state.activePortfolioId,
  );
  const showOpenTrades = useShowOpenTrades();
  const portfolioId = portfolioIdParam || storePortfolioId;

  const {
    data: allTrades,
    isLoading,
    isError,
  } = useQuery<Trade[], Error>({
    queryKey: [
      "trades-all-for-reports",
      portfolioId,
      filterConfig?.account_ids ?? null,
      filterConfig?.date_from ?? null,
      filterConfig?.date_to ?? null,
    ],
    queryFn: ({ signal }) => fetchAllTrades(portfolioId ?? undefined, signal),
    staleTime: 5 * 60 * 1000,
    enabled: Boolean(portfolioId),
  });

  // Apply filters client-side (trades are already cached)
  const trades = useMemo(() => {
    if (!allTrades) return undefined;
    let filtered = allTrades;
    const accountIds = filterConfig?.account_ids;

    if (accountIds && accountIds.length > 0) {
      filtered = filtered.filter(
        (t) => t.account_id && accountIds.includes(t.account_id),
      );
    }

    if (filterConfig?.date_from) {
      const from = new Date(`${filterConfig.date_from}T00:00:00Z`).getTime();
      filtered = filtered.filter(
        (t) => t.closed_at && new Date(t.closed_at).getTime() >= from,
      );
    }

    if (filterConfig?.date_to) {
      const to = new Date(`${filterConfig.date_to}T23:59:59Z`).getTime();
      filtered = filtered.filter(
        (t) => t.closed_at && new Date(t.closed_at).getTime() <= to,
      );
    }

    if (filterConfig?.playbook_ids && filterConfig.playbook_ids.length > 0) {
      filtered = filtered.filter(
        (t) =>
          t.playbook_id && filterConfig.playbook_ids!.includes(t.playbook_id),
      );
    }

    if (filterConfig?.taxonomy_ids && filterConfig.taxonomy_ids.length > 0) {
      filtered = filtered.filter((t) =>
        t.taxonomies?.some((tax) =>
          filterConfig.taxonomy_ids!.includes(tax.id),
        ),
      );
    }

    if (filterConfig?.symbols && filterConfig.symbols.length > 0) {
      filtered = filtered.filter(
        (t) =>
          t.symbol &&
          filterConfig.symbols!.some((sym) =>
            t.symbol.toUpperCase().startsWith(sym.toUpperCase()),
          ),
      );
    }

    if (
      filterConfig?.excluded_symbols &&
      filterConfig.excluded_symbols.length > 0
    ) {
      filtered = filtered.filter(
        (t) =>
          !t.symbol ||
          !filterConfig.excluded_symbols!.some((sym) =>
            t.symbol.toUpperCase().startsWith(sym.toUpperCase()),
          ),
      );
    }

    if (filterConfig?.asset_classes && filterConfig.asset_classes.length > 0) {
      filtered = filtered.filter(
        (t) =>
          t.asset_class && filterConfig.asset_classes!.includes(t.asset_class),
      );
    }

    const status = showOpenTrades ? filterConfig?.status : "closed";
    if (status === "closed") {
      filtered = filtered.filter(
        (t) => t.closed_at !== null && t.closed_at !== undefined,
      );
    } else if (status === "open") {
      filtered = filtered.filter(
        (t) => t.closed_at === null || t.closed_at === undefined,
      );
    }

    return filtered;
  }, [
    allTrades,
    filterConfig,
    showOpenTrades,
  ]);

  const calendarData = useMemo((): DailyTradeData[] => {
    if (!trades) return [];
    const groups = new Map<string, { pnl: number; tradeCount: number }>();
    trades.forEach((trade) => {
      if (!trade.closed_at) return;
      const dateKey = trade.closed_at.slice(0, 10);
      const tradePnl = parseFloat(trade.pnl || "0");
      const existing = groups.get(dateKey);
      if (existing) {
        existing.pnl += tradePnl;
        existing.tradeCount += 1;
      } else {
        groups.set(dateKey, { pnl: tradePnl, tradeCount: 1 });
      }
    });
    return Array.from(groups.entries()).map(([date, { pnl, tradeCount }]) => ({
      date,
      pnl,
      tradeCount,
    }));
  }, [trades]);

  function getAggregated(dimension: ReportDimension): PerformanceDataPoint[] {
    if (!trades) return [];
    const groups = new Map<string, Trade[]>();
    trades.forEach((trade) => {
      if (!trade.closed_at) return;
      const key = buildKey(new Date(trade.closed_at), dimension);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(trade);
    });

    const result: PerformanceDataPoint[] = [];
    groups.forEach((groupTrades, key) => {
      let pnl = 0,
        netPnl = 0,
        grossProfit = 0,
        grossLoss = 0;
      let returnWin = 0,
        returnLoss = 0,
        returnOthers = 0;
      let shares = 0,
        mistakes = 0,
        commissions = 0;
      let wins = 0,
        losses = 0;

      groupTrades.forEach((t) => {
        const tradePnl = parseFloat(t.pnl || "0");
        const tradeCommission = parseFloat(t.commission || "0");
        const tradeNetPnl =
          t.net_pnl != null
            ? parseFloat(t.net_pnl.toString())
            : tradePnl - tradeCommission;

        pnl += tradePnl;
        netPnl += tradeNetPnl;
        shares += parseFloat(t.quantity || "0");
        commissions += tradeCommission;
        mistakes += t.tags
          ? t.tags.filter((tag) =>
              tag.name.toLowerCase().includes("mistake"),
            ).length
          : 0;
        if (tradePnl > 0) {
          grossProfit += tradePnl;
          returnWin += tradePnl;
          wins++;
        } else if (tradePnl < 0) {
          grossLoss += Math.abs(tradePnl);
          returnLoss += tradePnl;
          losses++;
        } else {
          returnOthers += tradePnl;
        }
      });

      const tradesCount = groupTrades.length;
      const profitFactor =
        grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 99 : 0;
      const winPercent = tradesCount > 0 ? (wins / tradesCount) * 100 : 0;
      const avgReturn = tradesCount > 0 ? pnl / tradesCount : 0;
      const avgNetReturn = tradesCount > 0 ? netPnl / tradesCount : 0;
      const avgProfit = wins > 0 ? returnWin / wins : 0;
      const avgLoser = losses > 0 ? returnLoss / losses : 0;

      result.push({
        name: key,
        pnl,
        netPnl,
        profitFactor,
        returnWin,
        winPercent,
        returnLoss,
        returnOthers,
        trades: tradesCount,
        shares,
        mistakes,
        avgReturn,
        avgNetReturn,
        avgProfit,
        avgLoser,
        commissions,
      });
    });

    return sortResult(result, dimension);
  }

  return {
    trades: trades ?? [],
    calendarData,
    getAggregated,
    isLoading,
    isError,
  };
}
