/**
 * TradeChart — Smart candlestick chart for individual trades.
 *
 * Data flow:
 *   1. If NEXT_PUBLIC_MARKET_DATA_HUB_URL is not set → TradingView fallback.
 *   2. If set → fetch /prices/{symbol}/history?provider=lseg from the hub.
 *   3. Any API error → silent switch to TradingView fallback.
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

import { useEffect, useRef, useState, useCallback } from "react";
import type { AssetClass, Trade } from "@/lib/types";
import { parseOccSymbol } from "@/lib/parseOccSymbol";
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

const HUB_BASE =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_MARKET_DATA_HUB_URL ?? ""
    : "";

type Interval = "1h" | "4h" | "1d";

const INTERVAL_SECONDS: Record<Interval, number> = {
  "1h": 3600,
  "4h": 14400,
  "1d": 86400,
};

// Well-known index tickers (without the ^ prefix used by some data sources)
const INDEX_TICKERS = new Set([
  "SPX", "RUT", "NDX", "DJI", "COMP", "VIX", "OEX", "MID",
  "SPY", // technically ETF but often treated as index for data
]);

// ── Helpers ───────────────────────────────────────────────────────────────────

function isIndexSymbol(symbol: string, assetClass: AssetClass): boolean {
  const upper = symbol.toUpperCase().replace(/^\^/, "");
  return (assetClass as string) === "INDEX" || INDEX_TICKERS.has(upper);
}

function smartDefaultInterval(entryDate: Date, exitDate: Date | null): Interval {
  const end = exitDate ?? new Date();
  const diffMs = end.getTime() - entryDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays < 7 ? "1h" : "1d";
}

function buildApiUrl(
  symbol: string,
  interval: Interval,
  entryDate: Date,
  exitDate: Date | null,
  assetClass: AssetClass,
): string {
  const secs = INTERVAL_SECONDS[interval];
  const start = new Date(
    entryDate.getTime() - 30 * secs * 1000,
  ).toISOString();
  const end = new Date(
    (exitDate ?? new Date()).getTime() + 10 * secs * 1000,
  ).toISOString();

  const params = new URLSearchParams({
    provider: "lseg",
    interval,
    start,
    end,
  });

  if (isIndexSymbol(symbol, assetClass)) {
    params.set("sec_type", "index");
  }

  return `${HUB_BASE}/prices/${encodeURIComponent(symbol)}/history?${params.toString()}`;
}

function tvSymbol(symbol: string): string {
  // Remove leading ^ for TradingView URLs
  return symbol.replace(/^\^/, "");
}

// ── Types for API response ────────────────────────────────────────────────────

interface OhlcBar {
  time?: number | string;
  date?: string;
  timestamp?: number;
  open: number;
  high: number;
  low: number;
  close: number;
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
      // Accept various timestamp field names from the hub
      let ts: number | null = null;
      if (typeof bar.time === "number") ts = bar.time;
      else if (typeof bar.timestamp === "number") ts = bar.timestamp;
      else if (typeof bar.time === "string") ts = Math.floor(new Date(bar.time).getTime() / 1000);
      else if (typeof bar.date === "string") ts = Math.floor(new Date(bar.date).getTime() / 1000);

      if (ts === null || isNaN(ts)) return null;
      // If timestamp is in milliseconds (> year 3000 in seconds), convert
      if (ts > 32503680000) ts = Math.floor(ts / 1000);

      return {
        time: ts as Time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      };
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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
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
      <span className={`px-1.5 py-0.5 rounded text-xs font-bold border ${typeColor}`}>
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

// ── Main component ────────────────────────────────────────────────────────────

export interface TradeChartProps {
  trade: Trade;
}

export function TradeChart({ trade }: TradeChartProps) {
  const occ = parseOccSymbol(trade.symbol);

  // Chart symbol: for options use the underlying, otherwise raw symbol
  const chartSymbol = occ.isOption ? occ.underlying : occ.underlying;
  const assetClass = trade.asset_class;

  const entryDate = new Date(trade.opened_at);
  const exitDate = trade.closed_at ? new Date(trade.closed_at) : null;

  const [interval, setInterval] = useState<Interval>(() =>
    smartDefaultInterval(entryDate, exitDate)
  );
  const [loading, setLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(() => !HUB_BASE);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);

  // ── Fetch chart data ───────────────────────────────────────────────────────
  const fetchAndRender = useCallback(
    async (iv: Interval) => {
      if (!HUB_BASE) {
        setUseFallback(true);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const url = buildApiUrl(chartSymbol, iv, entryDate, exitDate, assetClass);
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

        const candles = mapBars(rawBars);

        if (seriesRef.current) {
          seriesRef.current.setData(candles);

          // ── Markers ──────────────────────────────────────────────────────
          const entryTs = Math.floor(entryDate.getTime() / 1000);
          const exitTs = exitDate ? Math.floor(exitDate.getTime() / 1000) : null;

          // Snap to nearest available bar time for the marker
          const snap = (target: number): Time => {
            let best = candles[0].time as number;
            let bestDiff = Math.abs(target - best);
            for (const c of candles) {
              const d = Math.abs(target - (c.time as number));
              if (d < bestDiff) { best = c.time as number; bestDiff = d; }
            }
            return best as Time;
          };

          const markers: SeriesMarker<Time>[] = [
            {
              time: snap(entryTs),
              position: "belowBar",
              color: "#26a69a",
              shape: "arrowUp",
              text: "Entry",
            },
          ];

          if (exitTs !== null) {
            markers.push({
              time: snap(exitTs),
              position: "aboveBar",
              color: "#ef5350",
              shape: "arrowDown",
              text: "Exit",
            });
          }

          // createSeriesMarkers is the v5 API (replaces series.setMarkers)
          if (markersRef.current) {
            markersRef.current.setMarkers(markers);
          } else if (seriesRef.current) {
            markersRef.current = createSeriesMarkers(seriesRef.current, markers);
          }

          // ── Fit visible range with context ───────────────────────────────
          const secs = INTERVAL_SECONDS[iv];
          chartRef.current?.timeScale().setVisibleRange({
            from: (entryTs - 30 * secs) as Time,
            to: ((exitTs ?? Math.floor(Date.now() / 1000)) + 10 * secs) as Time,
          });        }

        setUseFallback(false);
      } catch {
        setUseFallback(true);
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [chartSymbol, assetClass, trade.opened_at, trade.closed_at]
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
        vertLine: { color: "rgba(255,255,255,0.15)", labelBackgroundColor: "#1e1e2e" },
        horzLine: { color: "rgba(255,255,255,0.15)", labelBackgroundColor: "#1e1e2e" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
        textColor: "rgba(180,180,200,0.6)",
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
    if (!useFallback || HUB_BASE) {
      fetchAndRender(interval);
    }
  }, [interval, fetchAndRender, useFallback]);

  // ── Interval change handler ────────────────────────────────────────────────
  function handleIntervalChange(iv: Interval) {
    setInterval(iv);
  }

  // ── TradingView fallback (no Hub URL or API error) ─────────────────────────
  if (useFallback && !loading) {
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
      <div className="shrink-0 flex items-center gap-1 px-3 pt-2 pb-1">
        {(["1h", "4h", "1d"] as Interval[]).map((iv) => (
          <button
            key={iv}
            onClick={() => handleIntervalChange(iv)}
            className={`px-2.5 py-0.5 rounded text-xs font-mono font-medium transition-colors ${
              interval === iv
                ? "bg-primary/20 text-primary border border-primary/40"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50"
            }`}
          >
            {iv}
          </button>
        ))}
        <div className="flex-1" />
        {/* Open in TradingView */}
        <a
          href={`https://www.tradingview.com/chart/?symbol=${cleanSymbolForTV}`}
          target="_blank"
          rel="noopener noreferrer"
          title="Open in TradingView"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs text-zinc-400 hover:text-primary border border-transparent hover:border-border transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
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
