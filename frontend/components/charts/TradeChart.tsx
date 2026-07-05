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
 *     details (strike, expiry, type) are displayed as an overlay badge.
 *   - Index symbols (asset_class === "INDEX" or common index tickers like SPX,
 *     RUT, NDX, DJI): sec_type=index is appended to the API call.
 *   - TradingView link: "^" prefix is stripped from index symbols.
 */

"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type { AssetClass, Trade, LogicalExecution } from "@/lib/types";
import { parseOccSymbol } from "@/lib/parseOccSymbol";
import { formatPriceLabel } from "@/lib/executionPriceLabel";
import { useSettings } from "@/hooks/useSettings";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type Time,
  ColorType,
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
}

interface ChartCandle {
  time: Time; // UNIX seconds as Time
  open: number;
  high: number;
  low: number;
  close: number;
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

      // OHLC values may be strings — coerce to number.
      const open = Number(bar.open);
      const high = Number(bar.high);
      const low = Number(bar.low);
      const close = Number(bar.close);

      if ([open, high, low, close].some(isNaN)) return null;

      return { time: ts as Time, open, high, low, close };
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

// ── Options overlay badge ─────────────────────────────────────────────────────

function OptionOverlay({ occ }: { occ: ReturnType<typeof parseOccSymbol> }) {
  if (!occ.isOption) return null;
  const typeColor =
    occ.optionType === "Call"
      ? "text-emerald-400 bg-emerald-900/40 border-emerald-700/50"
      : "text-red-400 bg-red-900/40 border-red-700/50";

  return (
    <div className="absolute top-2 left-2 z-10 flex items-center gap-1.5 px-2 py-1 rounded-md bg-zinc-900/80 backdrop-blur-sm border border-border/50 text-xs">
      <span
        className={`px-1.5 py-0.5 rounded text-xs font-bold border ${typeColor}`}
      >
        {occ.optionType}
      </span>
      <span className="text-zinc-300 font-mono">{occ.strikeFormatted}</span>
      <span className="text-zinc-500">·</span>
      <span className="text-zinc-400">{occ.expiryFormatted}</span>
      <span className="text-zinc-500">·</span>
      <span className="text-zinc-500 text-[10px]">Underlying chart</span>
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
      : (["1h", "4h", "1d", "1w"] as Interval[]);
  }, [settings?.chart_intervals]);

  const occ = parseOccSymbol(trade.symbol);

  // Chart symbol: for options use the underlying, otherwise raw symbol
  const chartSymbol = occ.isOption ? occ.underlying : occ.underlying;
  const assetClass = trade.asset_class ?? "EQUITY";

  const entryDate = new Date(trade.opened_at);
  const exitDate = trade.closed_at ? new Date(trade.closed_at) : null;

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

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);

  // ── Fetch chart data ───────────────────────────────────────────────────────
  const fetchAndRender = useCallback(
    async (iv: Interval) => {
      setLoading(true);
      try {
        const url = buildApiUrl(
          chartSymbol,
          iv,
          entryDate,
          exitDate,
          assetClass,
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

          // Insert synthetic flat candles for any marker timestamp not covered
          // by an existing bar.  This guarantees the marker is rendered at the
          // correct chronological position even when the LSEG hub has a data gap
          // (e.g. the trade occurred weeks before the hub's earliest available bar).
          const synthetics: ChartCandle[] = [];
          for (const raw of markerTimestamps) {
            const ts = normalise(raw);
            if (!candleSet.has(ts)) {
              // Use the price from the nearest real candle as the synthetic close
              let nearest = candles[0];
              let bestDiff = Math.abs((candles[0].time as number) - ts);
              for (const c of candles) {
                const d = Math.abs((c.time as number) - ts);
                if (d < bestDiff) {
                  nearest = c;
                  bestDiff = d;
                }
              }
              const p = nearest.close;
              synthetics.push({
                time: ts as Time,
                open: p,
                high: p,
                low: p,
                close: p,
              });
              candleSet.add(ts);
            }
          }

          if (synthetics.length > 0) {
            candles = [...candles, ...synthetics].sort(
              (a, b) => (a.time as number) - (b.time as number),
            );
          }

          if (chartMode === "to-exit" && exitTs !== null) {
            const cutoff = exitTs;
            candles = candles.filter((c) => (c.time as number) <= cutoff);
          } else if (chartMode === "to-entry") {
            const cutoff = entryCutoffTs;
            candles = candles.filter((c) => (c.time as number) <= cutoff);
          }

          seriesRef.current.setData(candles);

          // Snap: map an exact timestamp to the closest available bar time.
          // Because we injected synthetic bars above, execution timestamps will
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
          const markers: SeriesMarker<Time>[] =
            activeExecutions && activeExecutions.length > 0
              ? buildExecutionMarkers(
                  activeExecutions,
                  trade.direction,
                  candles,
                  snap,
                )
              : buildFallbackMarkers(entryTs, activeExitTs, trade.direction, snap);

          // Spacing and overall marker styling
          seriesRef.current.applyOptions({
            markers: {
              offset: 20, // Even more space to clear the wicks
            },
          } as any);

          // createSeriesMarkers is the v5 API (replaces series.setMarkers)
          if (markersRef.current) {
            markersRef.current.setMarkers(markers);
          } else if (seriesRef.current) {
            markersRef.current = createSeriesMarkers(
              seriesRef.current,
              markers,
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
      } catch {
        setUseFallback(true);
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
        vertLine: {
          color: "rgba(255,255,255,0.15)",
          labelBackgroundColor: "#1e1e2e",
        },
        horzLine: {
          color: "rgba(255,255,255,0.15)",
          labelBackgroundColor: "#1e1e2e",
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

    chartRef.current = chart;
    seriesRef.current = series;

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

  // ── TradingView fallback (no Hub URL configured, or API error) ────────────
  if (useFallback) {
    return (
      <div className="w-full h-full relative">
        {occ.isOption && <OptionOverlay occ={occ} />}
        <TradingViewFallback symbol={chartSymbol} />
      </div>
    );
  }

  // ── Lightweight-charts render ─────────────────────────────────────────────
  const cleanSymbolForTV = tvSymbol(chartSymbol);

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Option overlay */}
      {occ.isOption && <OptionOverlay occ={occ} />}

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
      <div className="flex-1 relative min-h-0">
        {loading && (
          <div className="absolute inset-0 z-10">
            <ChartSkeleton />
          </div>
        )}
        <div
          ref={chartContainerRef}
          className="w-full h-full"
          style={{ opacity: loading ? 0 : 1, transition: "opacity 0.2s ease" }}
        />
      </div>
    </div>
  );
}
