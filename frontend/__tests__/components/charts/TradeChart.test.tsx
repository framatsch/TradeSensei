import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { createChart, createSeriesMarkers, CandlestickSeries, HistogramSeries } from "lightweight-charts";
import { formatPriceLabel } from "@/lib/executionPriceLabel";
import { TradeChart } from "@/components/charts/TradeChart";
import type { Trade, LogicalExecution } from "@/lib/types";

const mockFetch = jest.fn().mockResolvedValue({
  ok: true,
  json: async () => [
    { start: "2024-01-01T12:00:00Z", open: 100, high: 101, low: 99, close: 100, volume: 500 },
  ],
});
global.fetch = mockFetch;

jest.mock("lightweight-charts", () => ({
  createChart: jest.fn(() => ({
    addSeries: jest.fn(() => ({
      setData: jest.fn(),
      createPriceLine: jest.fn(),
      removePriceLine: jest.fn(),
      applyOptions: jest.fn(),
      priceScale: jest.fn(() => ({ applyOptions: jest.fn() })),
    })),
    timeScale: jest.fn(() => ({
      fitContent: jest.fn(),
      setVisibleRange: jest.fn(),
    })),
    subscribeCrosshairMove: jest.fn(),
    applyOptions: jest.fn(),
    remove: jest.fn(),
  })),
  createSeriesMarkers: jest.fn(() => ({ setMarkers: jest.fn() })),
  CandlestickSeries: jest.fn(),
  HistogramSeries: jest.fn(),
  ColorType: { Solid: "solid" },
  CrosshairMode: { Normal: 0, Hidden: 2 },
  LineStyle: { Dashed: 2 },
}), { virtual: true });

// Mock useSettings
jest.mock("@/hooks/useSettings", () => ({
  useSettings: () => ({ data: { chart_intervals: ["1h", "1d"] } }),
}));

describe("formatPriceLabel", () => {
  it("renders adjusted and raw when values differ", () => {
    expect(formatPriceLabel("50", "500")).toBe("$50.00 (raw: $500.00)");
  });

  it("renders only one value when adjusted equals raw", () => {
    expect(formatPriceLabel("50", "50")).toBe("$50.00");
    expect(formatPriceLabel("50.0", "50.00")).toBe("$50.00");
  });
});


global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};




describe("TradeChart", () => {
  const baseTrade: Trade = {
    id: "trade-1",
    symbol: "AAPL",
    direction: "LONG",
    asset_class: "EQUITY",
    is_combo: false,
    multiplier: 1,
    quantity: "10",
    entry_price: "100",
    exit_price: null,
    stop_loss: null,
    take_profit: null,
    opened_at: "2024-01-01T00:00:00Z",
    closed_at: null,
    pnl: null,
    net_pnl: null,
    commission: "0",
    journal: null,
    currency: "USD",
    pnl_eur: null,
    net_pnl_eur: null,
    tradingview_link: null,
    image_urls: [],
    playbook_id: null,
    playbook_name: null,
    account_id: "account-1",
    account_name: "Main",
    account_type: "ibkr",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    is_manually_edited: false,
    tags: [],
    position_id: "pos-1",
    user_rating: 0,
    trade_notes: [],
  };

  const baseExecution: LogicalExecution = {
    id: "exec-1",
    trade_id: "trade-1",
    user_id: "user-1",
    account_id: "account-1",
    symbol: "AAPL",
    asset_class: "EQUITY",
    conid: null,
    direction: "LONG",
    quantity: "10",
    price: "100",
    raw_quantity: "10",
    raw_price: "100",
    commission: "0",
    pnl: null,
    pnl_eur: null,
    executed_at: "2024-01-01T12:00:00Z",
    origin: "imported",
    deleted: false,
    user_modified: false,
    parent_id: null,
    currency: "USD",
    multiplier: 1,
    created_at: "2024-01-01T12:00:00Z",
    updated_at: "2024-01-01T12:00:00Z",
  };

  it("does not render option overlay controls for option trades (details page only, not chart)", async () => {
    // Per option-leg-contract-details spec: strike/expiry/type are shown on
    // the trade detail page (execution legs table / summary card), not as a
    // chart overlay. The chart renders the plain underlying candlestick chart
    // with no "Chart layers" popover, strike lines, or option chips.
    const tradeWithOptions: Trade = { ...baseTrade, asset_class: "OPTION", symbol: "QQQ   251003C00712000" };

    const optionExec: LogicalExecution = {
      ...baseExecution,
      symbol: "QQQ   251003C00712000",
      asset_class: "OPTION",
      option_type: "C",
      strike: "712",
      expiry: "2025-10-03",
    };

    render(<TradeChart trade={tradeWithOptions} executions={[optionExec]} />);

    await waitFor(() => expect(createSeriesMarkers).toHaveBeenCalled());
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining(
      "/api/proxy/api/v1/market-data/prices/QQQ/history?",
    ));
    const chart = jest.mocked(createChart).mock.results[0].value;
    expect(chart.addSeries).toHaveBeenCalledWith(CandlestickSeries, expect.any(Object));
    expect(chart.addSeries).toHaveBeenCalledWith(HistogramSeries, expect.any(Object));
    const candleSeries = jest.mocked(chart.addSeries).mock.results[0].value;
    expect(candleSeries.setData).toHaveBeenCalledWith([
      { time: 1704110400, open: 100, high: 101, low: 99, close: 100, volume: 500 },
    ]);
    expect(candleSeries.createPriceLine).not.toHaveBeenCalled();
    expect(screen.getByTitle("Refresh")).toBeEnabled();
    expect(screen.queryByTitle("Chart layers")).not.toBeInTheDocument();
    expect(screen.queryByText(/Call|Put/)).not.toBeInTheDocument();
    expect(screen.queryByText("712")).not.toBeInTheDocument();
  });
});
