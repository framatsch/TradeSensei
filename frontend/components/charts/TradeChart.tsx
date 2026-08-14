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
 * TradeChart — Smart candlestick chart for individual trades.
 *
 * Data flow:
 *   1. If NEXT_PUBLIC_MARKET_DATA_HUB_URL is not set → TradingView fallback.
 *   2. If set → fetch /prices/{symbol}/history?provider=lseg from the hub.
 *   3. Any API error → silent switch to TradingView fallback.
 *
 * Execution markers:
 *   - When `executions` prop is provided, per-execution markers are rendered.
 *   - Entry executions → arrowUp  belowBar  cyan   (#00d2ff) — always below the candle.
 *   - Exit  executions → arrowDown aboveBar orange (#f97316) — always above the candle.
 *   - "Entry" = execution whose direction matches the trade direction (BUY for LONG, SELL for SHORT).
 *   - Multiple same-role executions on the same candle are merged into one marker.
 *   - Fallback: if executions is empty/undefined, uses trade-level opened_at/closed_at.
 *
 * Special cases:
 *   - Options (asset_class === "OPTION"): OCC symbol is parsed to get the
 *     underlying ticker; chart always shows the underlying price. Contract
 *     details (strike, expiry, type) are shown on the trade detail page
 *     (execution legs table / summary card), not on the chart.
 *   - Index symbols (asset_class === "INDEX" or common index tickers like SPX,
 *     RUT, NDX, DJI): sec_type=index is appended to the API call.
 *   - TradingView link: "^" prefix is stripped from index symbols.
 */

"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type { AssetClass, Trade, LogicalExecution } from "@/lib/types";
import { parseOccSymbol } from "@/lib/parseOccSymbol";
import { formatPriceLabel } from "@/lib/executionPriceLabel";
import { formatSplitRatio } from "@/lib/formatSplitRatio";
import { useSettings } from "@/hooks/useSettings";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  type IPriceLine,
  ColorType,
  LineStyle,
  CrosshairMode,
} from "lightweight-charts";

// ── Config ────────────────────────────────────────────────────────────────────

// All browser-side API calls go through the Next.js reverse proxy at
// `/api/proxy/v1/...` — the backend is never contacted directly from the
// browser. This keeps the backend off the public internet and eliminates the
// need for absolute NEXT_PUBLIC_API_URL in the client.
const API_BASE = "/api/proxy";

const MARKET_DATA_PROXY = `${API_BASE}/api/v1/market-data`;

type Interval = "1h" | "4h" | "1d" | "1w";

const INTERVAL_SECONDS: Record<Interval, number> = {
  "1h": 3600,
  "4h": 14400,
  "1d": 86400,
  "1w": 604800,
};

// Well-known index tickers (without the ^ prefix used by some data sources)
const INDEX_TICKERS = new Set([
  "SPX",
  "RUT",
  "NDX",
  "DJI",
  "COMP",
  "VIX",
  "OEX",
  "MID",
  "SPY", // technically ETF but often treated as index for data
]);

// ── Helpers ───────────────────────────────────────────────────────────────────

function isIndexSymbol(symbol: string, assetClass: AssetClass): boolean {
  const upper = symbol.toUpperCase().replace(/^\^/, "");
  return (assetClass as string) === "INDEX" || INDEX_TICKERS.has(upper);
}

function smartDefaultInterval(
  entryDate: Date,
  exitDate: Date | null,
  allowedIntervals: Interval[],
): Interval {
  const fallback = allowedIntervals.length > 0 ? allowedIntervals[allowedIntervals.length - 1] : "1d";

  const now = Date.now();
  // If the trade is very old (entry is > 60 days ago), intraday data is likely unavailable.
  // The LSEG hub only keeps ~1000 bars of 1h data (approx 2.5 months).
  const daysSinceEntry = (now - entryDate.getTime()) / (1000 * 60 * 60 * 24);
  if (daysSinceEntry > 60) {
    if (allowedIntervals.includes("1d")) return "1d";
    return fallback;
  }

  const end = exitDate ?? new Date(now);
  const diffMs = end.getTime() - entryDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  
  if (diffDays < 7 && allowedIntervals.includes("1h")) return "1h";
  if (diffDays < 14 && allowedIntervals.includes("4h")) return "4h";
  if (allowedIntervals.includes("1d")) return "1d";
  return fallback;
}

function buildApiUrl(
  symbol: string,
  interval: Interval,
  entryDate: Date,
  exitDate: Date | null,
  assetClass: AssetClass,
  forceRefresh: boolean = false,
): string {
  const secs = INTERVAL_SECONDS[interval];
  // Buffer start by 30 candles
  const start = new Date(entryDate.getTime() - 30 * secs * 1000).toISOString();

  // We deliberately do NOT send `end` to the Market Data Hub.
  // The LSEG provider has a bug where if `end` is too far in the past,
  // it returns 0 bars. Omitting `end` safely fetches from `start` up to today.
  // Lightweight-charts will just render the extra bars, but our `setVisibleRange`
  // will keep the view focused correctly around the trade.
  const params = new URLSearchParams({
    provider: "lseg",
    interval,
    start,
  });

  if (isIndexSymbol(symbol, assetClass)) {
    params.set("sec_type", "index");
  }

  if (forceRefresh) {
    params.set("force_refresh", "true");
  }

  return `${MARKET_DATA_PROXY}/prices/${encodeURIComponent(symbol)}/history?${params.toString()}`;
}

function tvSymbol(symbol: string): string {
  // Remove leading ^ for TradingView URLs
  return symbol.replace(/^\^/, "");
}

// ── Types for API response ────────────────────────────────────────────────────

interface OhlcBar {
  // Hub uses "start" as the candle open time (ISO string).
  // Accept all common field names for forward compatibility.
  start?: string;
  end?: string;
  time?: number | string;
  date?: string;
  timestamp?: number;
  // OHLC values may come as strings from the Hub ("123.45") or numbers.
  open: number | string;
  high: number | string;
  low: number | string;
  close: number | string;
  volume?: number | string;
}

interface ChartCandle {
  time: Time; // UNIX seconds as Time
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

function mapBars(raw: OhlcBar[]): ChartCandle[] {
  return raw
    .map((bar): ChartCandle | null => {
      // Resolve timestamp — Hub uses "start" (ISO string) as primary field.
      let ts: number | null = null;
      if (typeof bar.start === "string") {
        ts = Math.floor(new Date(bar.start).getTime() / 1000);
      } else if (typeof bar.time === "number") {
        ts = bar.time;
      } else if (typeof bar.timestamp === "number") {
        ts = bar.timestamp;
      } else if (typeof bar.time === "string") {
        ts = Math.floor(new Date(bar.time).getTime() / 1000);
      } else if (typeof bar.date === "string") {
        ts = Math.floor(new Date(bar.date).getTime() / 1000);
      }

      if (ts === null || isNaN(ts)) return null;
      // Convert milliseconds → seconds if accidentally in ms (> year 3000 in sec)
      if (ts > 32503680000) ts = Math.floor(ts / 1000);

      const open = Number(bar.open);
      const high = Number(bar.high);
      const low = Number(bar.low);
      const close = Number(bar.close);
      const volume = Number(bar.volume || 0);

      if ([open, high, low, close].some(isNaN)) return null;
      if (open === 0 && high === 0 && low === 0 && close === 0) return null;

      return { time: ts as Time, open, high, low, close, volume };
    })
    .filter((b): b is ChartCandle => b !== null)
    .sort((a, b) => (a.time as number) - (b.time as number));
}

// ── TradingView fallback widget ───────────────────────────────────────────────

function TradingViewFallback({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cleanSymbol = tvSymbol(symbol);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "tradingview-widget-container__widget";
    wrapper.style.height = "100%";
    wrapper.style.width = "100%";
    container.appendChild(wrapper);

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: cleanSymbol,
      interval: "D",
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });
    container.appendChild(script);
  }, [cleanSymbol]);

  return (
    <div className="w-full h-full flex flex-col">
      <div ref={containerRef} className="tradingview-widget-container flex-1" />
      {/* TV open link */}
      <div className="shrink-0 flex justify-end px-3 py-1.5 border-t border-border/50">
        <a
          href={`https://www.tradingview.com/chart/?symbol=${cleanSymbol}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-primary transition-colors"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-3 h-3"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          Open in TradingView
        </a>
      </div>
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function ChartSkeleton() {
  return (
    <div className="w-full h-full flex flex-col gap-2 p-3 animate-pulse">
      <div className="flex gap-2 items-center">
        <div className="h-6 w-24 rounded bg-zinc-700/50" />
        <div className="h-6 w-16 rounded bg-zinc-700/30" />
        <div className="h-6 w-16 rounded bg-zinc-700/30" />
      </div>
      <div className="flex-1 rounded-lg bg-zinc-800/40" />
    </div>
  );
}

// ── Execution marker helpers ───────────────────────────────────────────────────

interface MarkerGroup {
  time: Time;
  position: "belowBar" | "aboveBar";
  color: string;
  shape: "arrowUp" | "arrowDown";
  text: string;
}

/** Marker style for an entry execution: cyan arrow ↑ below the bar. */
const ENTRY_STYLE = {
  position: "belowBar" as const,
  shape: "arrowUp" as const,
  color: "#00d2ff",
};
/** Marker style for an exit execution:  orange arrow ↓ above the bar. */
const EXIT_STYLE = {
  position: "aboveBar" as const,
  shape: "arrowDown" as const,
  color: "#f97316",
};

/**
 * Return true when `exec` is an opening (entry) execution for the given trade
 * direction.
 *   LONG  trade: entry = LONG/BUY execution
 *   SHORT trade: entry = SHORT/SELL execution
 */
function isEntryExecution(
  exec: LogicalExecution,
  tradeDirection: string,
): boolean {
  const td = tradeDirection.toUpperCase();
  const ed = exec.direction.toUpperCase();
  return td === "LONG"
    ? ed === "LONG" || ed === "BUY"
    : ed === "SHORT" || ed === "SELL";
}

/**
 * Build SeriesMarkers from a list of LogicalExecutions.
 * Executions on the same candle time and same role (entry/exit) are merged.
 */
function buildExecutionMarkers(
  executions: LogicalExecution[],
  tradeDirection: string,
  candles: ChartCandle[],
  snap: (target: number) => Time,
): SeriesMarker<Time>[] {
  if (executions.length === 0) return [];

  // Group by snapped candle time + role (entry vs exit)
  const groups = new Map<
    string,
    {
      isEntry: boolean;
      qtys: string[];
      adjustedPrices: string[];
      rawPrices: string[];
      time: Time;
    }
  >();

  for (const exec of executions) {
    const ts = Math.floor(new Date(exec.executed_at).getTime() / 1000);
    const snapped = snap(ts);
    const isEntry = isEntryExecution(exec, tradeDirection);
    const key = `${snapped as number}-${isEntry ? "entry" : "exit"}`;

    const existing = groups.get(key);
    if (existing) {
      existing.qtys.push(exec.quantity);
      existing.adjustedPrices.push(exec.price);
      existing.rawPrices.push(exec.raw_price);
    } else {
      groups.set(key, {
        isEntry,
        qtys: [exec.quantity],
        adjustedPrices: [exec.price],
        rawPrices: [exec.raw_price],
        time: snapped,
      });
    }
  }

  const markers: SeriesMarker<Time>[] = [];

  for (const [, group] of groups) {
    // Hover label with quantity and price details
    const detailedLabel =
      group.qtys.length === 1
        ? `${Number(group.qtys[0]).toFixed(2)} @ ${formatPriceLabel(group.adjustedPrices[0], group.rawPrices[0])}`
        : group.qtys
            .map(
              (q, i) =>
                `${Number(q).toFixed(2)} @ ${formatPriceLabel(group.adjustedPrices[i], group.rawPrices[i])}`,
            )
            .join(", ");

    const style = group.isEntry ? ENTRY_STYLE : EXIT_STYLE;

    markers.push({
      time: group.time,
      position: style.position,
      color: style.color,
      shape: style.shape,
      text: detailedLabel,
      size: 2,
    });
  }

  // Sort markers by time (required by lightweight-charts)
  markers.sort((a, b) => (a.time as number) - (b.time as number));

  // Deduplicate markers at exact same time + same position (keep first, merge text)
  const deduped: SeriesMarker<Time>[] = [];
  for (const m of markers) {
    const last = deduped[deduped.length - 1];
    if (last && last.time === m.time && last.position === m.position) {
      last.text = `${last.text} / ${m.text}`;
    } else {
      deduped.push(m);
    }
  }

  return deduped;
}

/**
 * Fallback markers using trade-level opened_at / closed_at timestamps.
 * Entry always cyan ↑ below, exit always orange ↓ above.
 */
function buildFallbackMarkers(
  entryTs: number,
  exitTs: number | null,
  _tradeDirection: string,
  snap: (target: number) => Time,
): SeriesMarker<Time>[] {
  const markers: SeriesMarker<Time>[] = [
    { time: snap(entryTs), ...ENTRY_STYLE, text: "ENTRY", size: 2 },
  ];
  if (exitTs !== null) {
    markers.push({ time: snap(exitTs), ...EXIT_STYLE, text: "EXIT", size: 2 });
  }
  return markers;
}

/**
 * Marker style for a corporate-action event: amber circle, in-bar.
 * Uses the same amber tone as the corporate-action disclosure banner
 * (`--warning`), so the chart marker reads as the same "Split" cue used on
 * the trade table indicator, the event row, and the per-leg mark.
 */
const CORPORATE_ACTION_STYLE = {
  position: "inBar" as const,
  shape: "circle" as const,
  color: "#f59e0b",
};

/**
 * Build one marker per corporate action affecting this trade's symbol, placed
 * at the action's effective date. This is the chart-level counterpart of the
 * execution-legs "Corporate Action" event row — same "Split <ratio> on <date>"
 * wording, same visual cue, different surface.
 */
function buildCorporateActionMarkers(
  corporateActionImpact: NonNullable<Trade["corporate_action_impact"]> | undefined,
  candles: ChartCandle[],
  snap: (target: number) => Time,
): SeriesMarker<Time>[] {
  if (!corporateActionImpact || corporateActionImpact.length === 0 || candles.length === 0) {
    return [];
  }

  const firstCandleTs = candles[0].time as number;
  const lastCandleTs = candles[candles.length - 1].time as number;

  const markers: SeriesMarker<Time>[] = [];
  for (const action of corporateActionImpact) {
    const actionTs = Math.floor(new Date(action.date + "T00:00:00Z").getTime() / 1000);
    // Only place a marker if the effective date falls within the rendered range;
    // otherwise `snap` would clamp it to the nearest edge candle, misleadingly
    // suggesting the split happened at the start/end of the visible chart.
    if (actionTs < firstCandleTs || actionTs > lastCandleTs) continue;

    markers.push({
      time: snap(actionTs),
      ...CORPORATE_ACTION_STYLE,
      text: `Split ${formatSplitRatio(action.ratio)} on ${action.date}`,
      size: 1,
    });
  }
  return markers;
}

// ── Main component ────────────────────────────────────────────────────────────

export interface TradeChartProps {
  trade: Trade;
  /** Optional list of execution legs. When provided, per-execution markers are
   *  rendered instead of the single ENTRY/EXIT fallback. */
  executions?: LogicalExecution[];
}

export function TradeChart({ trade, executions }: TradeChartProps) {
  const { data: settings } = useSettings();

  const allowedIntervals = useMemo(() => {
    return settings?.chart_intervals && settings.chart_intervals.length > 0 
      ? settings.chart_intervals as Interval[] 
      : (["1h", "1d", "1w"] as Interval[]);
  }, [settings?.chart_intervals]);

  const occ = parseOccSymbol(trade.symbol);

  // Chart symbol: for options use the underlying, otherwise raw symbol
  const chartSymbol = occ.isOption ? occ.underlying : occ.underlying;
  const assetClass = trade.asset_class ?? "EQUITY";

  const entryDate = new Date(trade.opened_at);
  const exitDate = trade.closed_at ? new Date(trade.closed_at) : null;
  const lineEntryPrice = trade.chart_entry_price ?? trade.entry_price;
  const lineExitPrice = trade.chart_exit_price ?? trade.exit_price;

  const [interval, setInterval] = useState<Interval>(() =>
    smartDefaultInterval(entryDate, exitDate, allowedIntervals),
  );

  // Sync interval if allowedIntervals changes and the current one is not allowed
  useEffect(() => {
    if (!allowedIntervals.includes(interval)) {
      setInterval(smartDefaultInterval(entryDate, exitDate, allowedIntervals));
    }
  }, [allowedIntervals, interval, entryDate, exitDate]);
  const [chartMode, setChartMode] = useState<"full" | "to-exit" | "to-entry">(
    "full",
  );
  // If no Hub URL is configured we go straight to fallback — no loading needed
  const [loading, setLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(false);
  const [noData, setNoData] = useState(false);
  const [showTradeLines, setShowTradeLines] = useState(true);
  const showTradeLinesRef = useRef(true);
  const [showMarkers, setShowMarkers] = useState(true);
  const showMarkersRef = useRef(true);
  const [showVolume, setShowVolume] = useState(true);
  const showVolumeRef = useRef(true);
  const [showCrosshair, setShowCrosshair] = useState(true);
  const showCrosshairRef = useRef(true);
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const markersDataRef = useRef<SeriesMarker<Time>[]>([]);
  const priceLinesRef = useRef<IPriceLine[]>([]);

  // ── Fetch chart data ───────────────────────────────────────────────────────
  const fetchAndRender = useCallback(
    async (iv: Interval, forceRefresh: boolean = false) => {
      setLoading(true);
      setNoData(false);
      try {
        const url = buildApiUrl(
          chartSymbol,
          iv,
          entryDate,
          exitDate,
          assetClass,
          forceRefresh
        );
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();

        // Hub may return { data: [...] } envelope or a plain array
        const rawBars: OhlcBar[] = Array.isArray(json)
          ? json
          : Array.isArray(json?.data)
            ? json.data
            : Array.isArray(json?.prices)
              ? json.prices
              : [];

        if (rawBars.length === 0) throw new Error("No data returned");

        let candles = mapBars(rawBars);

        if (seriesRef.current) {
          // ── Marker timestamps ─────────────────────────────────────────────
          const entryTs = Math.floor(entryDate.getTime() / 1000);
          const exitTs = exitDate
            ? Math.floor(exitDate.getTime() / 1000)
            : null;

          // Collect all execution timestamps that need markers
          let activeExecutions = executions;
          let activeExitTs = exitTs;

          if (chartMode === "to-entry") {
            if (activeExecutions) {
              activeExecutions = activeExecutions.filter((e) =>
                isEntryExecution(e, trade.direction),
              );
            }
            activeExitTs = null;
          }

          // Determine the actual cutoff timestamp for "to-entry" mode
          let entryCutoffTs = entryTs;
          if (chartMode === "to-entry" && activeExecutions && activeExecutions.length > 0) {
            const maxEntryMs = Math.max(
              ...activeExecutions.map((e) => new Date(e.executed_at).getTime())
            );
            entryCutoffTs = Math.floor(maxEntryMs / 1000);
          }

          // Use activeExecutions instead of executions for marker timestamps
          const markerTimestamps: number[] =
            activeExecutions && activeExecutions.length > 0
              ? activeExecutions.map((e) =>
                  Math.floor(new Date(e.executed_at).getTime() / 1000),
                )
              : [entryCutoffTs, ...(activeExitTs !== null ? [activeExitTs] : [])];

          // For 1d charts, normalise timestamps to midnight UTC so they align
          // with daily bars (LSEG bars always open at 00:00 UTC).
          const SECS_PER_DAY = 86400;
          const normalise = (ts: number): number =>
            interval === "1d"
              ? Math.floor(ts / SECS_PER_DAY) * SECS_PER_DAY
              : ts;

          const candleSet = new Set(candles.map((c) => c.time as number));

          if (chartMode === "to-exit" && exitTs !== null) {
            const cutoff = exitTs;
            candles = candles.filter((c) => (c.time as number) <= cutoff);
          } else if (chartMode === "to-entry") {
            const cutoff = entryCutoffTs;
            candles = candles.filter((c) => (c.time as number) <= cutoff);
          }

          chartRef.current?.applyOptions({
            timeScale: {
              timeVisible: iv === "1h" || iv === "4h",
            }
          });

          seriesRef.current.setData(candles);
          
          if (volumeSeriesRef.current) {
            volumeSeriesRef.current.setData(
              candles.map(c => ({
                time: c.time,
                value: c.volume || 0,
                color: c.close >= c.open ? "rgba(38, 166, 154, 0.4)" : "rgba(239, 83, 80, 0.4)"
              }))
            );
          }

          // Clear old price lines
          if (priceLinesRef.current) {
            priceLinesRef.current.forEach((pl) => seriesRef.current?.removePriceLine(pl));
            priceLinesRef.current = [];
          }

          // Add horizontal price lines for entry and exit
          if (showTradeLinesRef.current) {
            if (lineEntryPrice) {
              const pl = seriesRef.current.createPriceLine({
                price: parseFloat(lineEntryPrice),
                color: "#00d2ff", // Cyan
                lineWidth: 2,
                lineStyle: LineStyle.Dashed,
                axisLabelVisible: true,
                title: "Entry",
              });
              priceLinesRef.current.push(pl);
            }
            if (lineExitPrice) {
              const pl = seriesRef.current.createPriceLine({
                price: parseFloat(lineExitPrice),
                color: "#f97316", // Orange
                lineWidth: 2,
                lineStyle: LineStyle.Dashed,
                axisLabelVisible: true,
                title: "Exit",
              });
              priceLinesRef.current.push(pl);
            }
          }

          // Snap: map an exact timestamp to the closest available bar time.
          // always find an exact or very close match.
          const snap = (target: number): Time => {
            const norm = normalise(target);
            if (candleSet.has(norm)) return norm as Time;
            let best = candles[0].time as number;
            let bestDiff = Math.abs(norm - best);
            for (const c of candles) {
              const d = Math.abs(norm - (c.time as number));
              if (d < bestDiff) {
                best = c.time as number;
                bestDiff = d;
              }
            }
            return best as Time;
          };

          // Use per-execution markers when available; fall back to trade-level timestamps
          const executionMarkers: SeriesMarker<Time>[] =
            activeExecutions && activeExecutions.length > 0
              ? buildExecutionMarkers(
                  activeExecutions,
                  trade.direction,
                  candles,
                  snap,
                )
              : buildFallbackMarkers(entryTs, activeExitTs, trade.direction, snap);

          // Corporate-action markers: chart-level counterpart of the execution-legs
          // "Corporate Action" event row, same visual cue as the table indicator and
          // per-leg mark (see buildCorporateActionMarkers doc comment).
          const corporateActionMarkers = buildCorporateActionMarkers(
            trade.corporate_action_impact,
            candles,
            snap,
          );

          const finalMarkers: SeriesMarker<Time>[] = [
            ...executionMarkers,
            ...corporateActionMarkers,
          ].sort((a, b) => (a.time as number) - (b.time as number));

          markersDataRef.current = finalMarkers;

          // Spacing and overall marker styling
          seriesRef.current.applyOptions({
            markers: {
              offset: 20, // Even more space to clear the wicks
            },
          } as any);

          if (markersRef.current) {
            markersRef.current.setMarkers(showMarkersRef.current ? finalMarkers : []);
          } else if (seriesRef.current) {
            markersRef.current = createSeriesMarkers(
              seriesRef.current,
              showMarkersRef.current ? finalMarkers : [],
            );
          }

          // ── Fit visible range with context ───────────────────────────────
          const secs = INTERVAL_SECONDS[iv];
          let toTime = (exitTs ?? Math.floor(Date.now() / 1000)) + 5 * secs;
          if (chartMode === "to-entry") {
            toTime = entryCutoffTs + 5 * secs;
          } else if (chartMode === "to-exit" && exitTs !== null) {
            toTime = exitTs + 5 * secs;
          }

          chartRef.current?.timeScale().setVisibleRange({
            from: (entryTs - 30 * secs) as Time,
            to: toTime as Time,
          });
        }

        setUseFallback(false);
      } catch (e: any) {
        // HTTP 503 is the expected signal from the backend that the Market Data Hub
        // is not configured. We fall back to TradingView silently.
        if (e instanceof Error && e.message.includes("HTTP 503")) {
          setUseFallback(true);
        } else if (e instanceof Error && e.message.includes("HTTP 404")) {
          // 404 means the symbol was not found by the data provider. Handle silently.
          setNoData(true);
        } else {
          // For other errors or "No data returned", we show the empty state instead of TradingView
          if (!(e instanceof Error) || !e.message.includes("No data returned")) {
            console.error("fetchAndRender error:", e);
          }
          setNoData(true);
        }
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      chartSymbol,
      assetClass,
      trade.opened_at,
      trade.closed_at,
      trade.direction,
      trade.entry_price,
      trade.exit_price,
      trade.chart_entry_price,
      trade.chart_exit_price,
      executions,
      chartMode,
    ],
  );

  // ── Create chart instance ──────────────────────────────────────────────────
  useEffect(() => {
    if (!chartContainerRef.current || useFallback) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(180,180,200,0.8)",
        fontFamily: "monospace",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        mode: showCrosshairRef.current ? CrosshairMode.Normal : CrosshairMode.Hidden,
        vertLine: {
          width: 1,
          color: "#a1a1aa",
          style: LineStyle.Dashed,
          labelBackgroundColor: "#2B2B43",
          visible: true,
          labelVisible: true,
        },
        horzLine: {
          width: 1,
          color: "#a1a1aa",
          style: LineStyle.Dashed,
          labelBackgroundColor: "#2B2B43",
          visible: true,
          labelVisible: true,
        },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
        textColor: "rgba(180,180,200,0.6)",
        scaleMargins: {
          top: 0.2,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: true,
      handleScale: true,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "", 
      visible: showVolumeRef.current,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    seriesRef.current = series;
    volumeSeriesRef.current = volumeSeries;

    // Responsive resize
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry && chartRef.current) {
        chartRef.current.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(chartContainerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      volumeSeriesRef.current = null;
      markersRef.current = null;
    };
  }, [useFallback]);

  // ── Fetch on mount + interval change ──────────────────────────────────────
  useEffect(() => {
    // Don't retry after a fallback-triggering error (e.g. 503 = hub not configured)
    if (!useFallback) {
      fetchAndRender(interval);
    }
  }, [interval, fetchAndRender, useFallback]);

  // ── Interval change handler ────────────────────────────────────────────────
  function handleIntervalChange(iv: Interval) {
    setInterval(iv);
  }

  // ── Trade lines toggle handlers ───────────────────────────────────────────
  function handleToggleTradeLines() {
    const nextVal = !showTradeLines;
    setShowTradeLines(nextVal);
    showTradeLinesRef.current = nextVal;

    if (!seriesRef.current) return;

    // Remove existing lines
    if (priceLinesRef.current) {
      priceLinesRef.current.forEach(pl => seriesRef.current?.removePriceLine(pl));
      priceLinesRef.current = [];
    }

    // Add lines back if enabled
    if (nextVal) {
      if (lineEntryPrice) {
        const pl = seriesRef.current.createPriceLine({
          price: parseFloat(lineEntryPrice),
          color: "#00d2ff",
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "Entry",
        });
        priceLinesRef.current.push(pl);
      }
      if (lineExitPrice) {
        const pl = seriesRef.current.createPriceLine({
          price: parseFloat(lineExitPrice),
          color: "#f97316",
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "Exit",
        });
        priceLinesRef.current.push(pl);
      }
    }
  }

  function handleToggleMarkers() {
    const nextVal = !showMarkers;
    setShowMarkers(nextVal);
    showMarkersRef.current = nextVal;

    if (markersRef.current) {
      markersRef.current.setMarkers(nextVal ? markersDataRef.current : []);
    }
  }

  function handleToggleVolume() {
    const nextVal = !showVolume;
    setShowVolume(nextVal);
    showVolumeRef.current = nextVal;

    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.applyOptions({ visible: nextVal });
    }
  }

  function handleToggleCrosshair() {
    const nextVal = !showCrosshair;
    setShowCrosshair(nextVal);
    showCrosshairRef.current = nextVal;

    if (chartRef.current) {
      chartRef.current.applyOptions({
        crosshair: {
          mode: nextVal ? CrosshairMode.Normal : CrosshairMode.Hidden,
        }
      });
    }
  }

  // ── TradingView fallback (no Hub URL configured, or API error) ────────────
  if (useFallback) {
    return (
      <div className="w-full h-full relative">
        <TradingViewFallback symbol={chartSymbol} />
      </div>
    );
  }

  // ── Lightweight-charts render ─────────────────────────────────────────────
  const cleanSymbolForTV = tvSymbol(chartSymbol);

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Interval toolbar */}
      <div className="shrink-0 flex items-center gap-1.5 px-3 pt-3 pb-2">
        <div className="flex p-0.5 rounded-full bg-secondary border border-border backdrop-blur-md shadow-inner">
          {allowedIntervals.map((iv) => (
            <button
              key={iv}
              onClick={() => handleIntervalChange(iv)}
              className={`relative px-3.5 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all duration-300 ${
                interval === iv
                  ? "bg-primary text-primary-foreground border border-primary/80"
                  : "text-muted-foreground hover:text-foreground hover:bg-foreground/5 border border-transparent"
              }`}
            >
              {iv}
              {interval === iv && (
                <span className="hidden dark:block absolute inset-0 rounded-full bg-primary/10 blur-[2px] animate-pulse" />
              )}
            </button>
          ))}
        </div>

        <div className="relative">
          <select
            value={chartMode}
            onChange={(e) => setChartMode(e.target.value as any)}
            className="appearance-none px-3 pr-7 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all duration-300 border bg-secondary text-muted-foreground border-border hover:text-foreground hover:bg-secondary/80 outline-none cursor-pointer shadow-inner"
            title="Chart Data Range"
          >
            <option value="full">Full Chart</option>
            {trade.closed_at && <option value="to-exit">Up to Exit</option>}
            <option value="to-entry">Up to Entry</option>
          </select>
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none opacity-50">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="w-3 h-3"
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={() => fetchAndRender(interval, true)}
            title="Refresh"
            disabled={loading}
            className={`flex items-center justify-center p-1.5 rounded-full transition-all duration-300 border shadow-inner ${
              loading
                ? "bg-secondary border-border text-muted-foreground opacity-50 cursor-not-allowed"
                : "bg-secondary text-muted-foreground border-border hover:text-foreground hover:bg-secondary/80"
            }`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}>
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
          </button>
        </div>

        <div className="relative">
          <button
            onClick={() => setIsOptionsOpen(!isOptionsOpen)}
            title="Chart Display Options"
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] uppercase tracking-wider font-bold transition-all duration-300 border shadow-inner ${
              isOptionsOpen
                ? "bg-primary/20 text-primary border-primary/30"
                : "bg-secondary text-muted-foreground border-border hover:text-foreground hover:bg-secondary/80"
            }`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="w-3 h-3">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            <span className="hidden sm:inline">Options</span>
          </button>
          
          {isOptionsOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsOptionsOpen(false)} />
              <div className="absolute right-0 sm:left-0 sm:right-auto top-full mt-2 w-48 bg-card border border-border rounded-xl shadow-xl z-50 p-2 flex flex-col gap-1">
                <label className="flex items-center gap-2.5 p-2 hover:bg-secondary/50 rounded-lg cursor-pointer text-sm">
                  <input type="checkbox" checked={showTradeLines} onChange={handleToggleTradeLines} className="w-4 h-4 rounded border-border text-primary focus:ring-primary/30" />
                  <span className="text-foreground">Price Lines</span>
                </label>
                <label className="flex items-center gap-2.5 p-2 hover:bg-secondary/50 rounded-lg cursor-pointer text-sm">
                  <input type="checkbox" checked={showMarkers} onChange={handleToggleMarkers} className="w-4 h-4 rounded border-border text-primary focus:ring-primary/30" />
                  <span className="text-foreground">Execution Arrows</span>
                </label>
                <label className="flex items-center gap-2.5 p-2 hover:bg-secondary/50 rounded-lg cursor-pointer text-sm">
                  <input type="checkbox" checked={showVolume} onChange={handleToggleVolume} className="w-4 h-4 rounded border-border text-primary focus:ring-primary/30" />
                  <span className="text-foreground">Volume</span>
                </label>
                <label className="flex items-center gap-2.5 p-2 hover:bg-secondary/50 rounded-lg cursor-pointer text-sm">
                  <input type="checkbox" checked={showCrosshair} onChange={handleToggleCrosshair} className="w-4 h-4 rounded border-border text-primary focus:ring-primary/30" />
                  <span className="text-foreground">Crosshair</span>
                </label>
              </div>
            </>
          )}
        </div>

        <div className="flex-1" />
        {/* Open in TradingView */}
        <a
          href={`https://www.tradingview.com/chart/?symbol=${cleanSymbolForTV}`}
          target="_blank"
          rel="noopener noreferrer"
          title="Open in TradingView"
          className="group inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] uppercase tracking-widest font-bold bg-primary text-primary-foreground hover:opacity-90 border border-primary/80 transition-all duration-300 shadow-sm"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className="w-3 h-3 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          TradingView
        </a>
      </div>

      {/* Chart canvas */}
      <div className="flex-1 relative min-h-0 bg-background/50">
        {loading && (
          <div className="absolute inset-0 z-10">
            <ChartSkeleton />
          </div>
        )}
        {noData && !loading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center p-4">
            <div className="bg-secondary/40 border border-border/50 px-6 py-5 rounded-2xl flex flex-col items-center gap-3 max-w-sm text-center backdrop-blur-sm shadow-sm">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8 text-muted-foreground/60">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="11" y1="8" x2="11" y2="14" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
              <div>
                <p className="text-sm font-bold text-foreground tracking-wide">No Market Data Available</p>
                <p className="text-xs text-muted-foreground leading-relaxed mt-1">The Market Data Hub returned no price data for the selected interval ({interval}).</p>
              </div>
            </div>
          </div>
        )}
        <div
          ref={chartContainerRef}
          className="w-full h-full"
          style={{ opacity: loading || noData ? 0 : 1, transition: "opacity 0.2s ease" }}
        />
      </div>
    </div>
  );
}
