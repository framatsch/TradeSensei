/**
 * React Query hooks for trade list fetching and bulk operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listTradesApiV1PortfoliosPortfolioIdTradesGet,
  bulkDeleteTradesApiV1PortfoliosPortfolioIdTradesBulkDeletePost,
  bulkAssignTagsApiV1PortfoliosPortfolioIdTradesBulkAssignTagsPost,
  bulkAssignPlaybookApiV1PortfoliosPortfolioIdTradesBulkAssignPlaybookPost,
  deprecatedTradesApiV1TradesGet,
} from "@/lib/api/index";
import type { CursorPage, ResponseEnvelope, Trade } from "@/lib/types";

// ─── Filter & sort types ──────────────────────────────────────────────────────

export interface TradeFilters {
  symbol?: string;
  direction?: string;
  asset_classes?: string[];
  opened_at_from?: string;
  opened_at_to?: string;
  closed_at_from?: string;
  closed_at_to?: string;
  tag_ids?: string[];
  playbook_id?: string;
  pnl_positive?: boolean | null;
  status?: "open" | "closed" | null;
  /** Filter by hour of day (0–23) the trade was opened. */
  hour_of_day?: number;
  /** Filter by day of week the trade was opened (0=Monday, …, 6=Sunday). */
  day_of_week?: number;
}

export interface TradeSortConfig {
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}

export interface UseTradesOptions {
  portfolioId?: string;
  cursor?: string | null;
  limit?: number;
  filters?: TradeFilters;
  sort?: TradeSortConfig;
}

// ─── Bulk operation payload types ────────────────────────────────────────────

interface BulkDeletePayload {
  trade_ids: string[];
  portfolio_id: string;
}

interface BulkAssignTagPayload {
  trade_ids: string[];
  tag_ids: string[];
  portfolio_id: string;
}

interface BulkAssignPlaybookPayload {
  trade_ids: string[];
  playbook_id: string | null;
  portfolio_id: string;
}

// ─── Date helpers ─────────────────────────────────────────────────────────────

/**
 * Ensure a date string is timezone-aware for the backend.
 * If it's a plain date like "2026-03-03" expand it to a full UTC timestamp.
 * If it already contains a timezone offset leave it unchanged.
 */
function toUtcFrom(dateStr: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return `${dateStr}T00:00:00Z`;
  return dateStr;
}

function toUtcTo(dateStr: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return `${dateStr}T23:59:59Z`;
  return dateStr;
}

// ─── useTrades ────────────────────────────────────────────────────────────────

export function useTrades({
  portfolioId,
  cursor,
  limit = 20,
  filters,
  sort,
}: UseTradesOptions = {}) {
  return useQuery<CursorPage<Trade>, Error>({
    queryKey: ["trades", portfolioId, cursor, limit, filters, sort],
    queryFn: async () => {
      if (portfolioId) {
        const { data, error } = await listTradesApiV1PortfoliosPortfolioIdTradesGet({
          path: { portfolio_id: portfolioId },
          query: {
            limit,
            cursor: cursor ?? undefined,
            symbol: filters?.symbol ?? undefined,
            direction: filters?.direction as import("@/lib/api/types.gen").Direction | undefined,
            tag_ids: filters?.tag_ids ?? undefined,
            tag_filter_mode: filters?.tag_ids?.length ? "or" : undefined,
            playbook_id: filters?.playbook_id ?? undefined,
            pnl_positive: filters?.pnl_positive ?? undefined,
            status: filters?.status ?? undefined,
            hour_of_day: filters?.hour_of_day ?? undefined,
            day_of_week: filters?.day_of_week ?? undefined,
            opened_at_from: filters?.opened_at_from ? toUtcFrom(filters.opened_at_from) : undefined,
            opened_at_to: filters?.opened_at_to ? toUtcTo(filters.opened_at_to) : undefined,
            closed_at_from: filters?.closed_at_from ? toUtcFrom(filters.closed_at_from) : undefined,
            closed_at_to: filters?.closed_at_to ? toUtcTo(filters.closed_at_to) : undefined,
            sort_by: sort?.sort_by as import("@/lib/api/types.gen").TradeSortField | undefined,
            sort_dir: sort?.sort_dir ?? undefined,
          },
        });
        if (error || !data) throw error;
        return (data as unknown as ResponseEnvelope<CursorPage<Trade>>).data;
      }

      // No portfolioId — use deprecated endpoint
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      if (cursor) params.set("cursor", cursor);
      if (filters) {
        if (filters.symbol) params.set("symbol", filters.symbol);
        if (filters.direction) params.set("direction", filters.direction);
        if (filters.asset_classes?.length) {
          for (const ac of filters.asset_classes) params.append("asset_class", ac);
        }
        if (filters.opened_at_from) params.set("opened_at_from", toUtcFrom(filters.opened_at_from));
        if (filters.opened_at_to) params.set("opened_at_to", toUtcTo(filters.opened_at_to));
        if (filters.closed_at_from) params.set("closed_at_from", toUtcFrom(filters.closed_at_from));
        if (filters.closed_at_to) params.set("closed_at_to", toUtcTo(filters.closed_at_to));
        if (filters.tag_ids?.length) {
          for (const tid of filters.tag_ids) params.append("tag_ids", tid);
          params.set("tag_filter_mode", "or");
        }
        if (filters.playbook_id) params.set("playbook_id", filters.playbook_id);
        if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) {
          params.set("pnl_positive", String(filters.pnl_positive));
        }
        if (filters.status) params.set("status", filters.status);
        if (filters.hour_of_day !== undefined && filters.hour_of_day !== null) {
          params.set("hour_of_day", String(filters.hour_of_day));
        }
        if (filters.day_of_week !== undefined && filters.day_of_week !== null) {
          params.set("day_of_week", String(filters.day_of_week));
        }
      }
      if (sort) {
        if (sort.sort_by) params.set("sort_by", sort.sort_by);
        if (sort.sort_dir) params.set("sort_dir", sort.sort_dir);
      }

      // The deprecated endpoint accepts query params via the URL; pass them as query object
      const { data, error } = await deprecatedTradesApiV1TradesGet();
      if (error || !data) throw error;
      return (data as unknown as ResponseEnvelope<CursorPage<Trade>>).data;
    },
    enabled: portfolioId !== undefined || portfolioId === undefined, // Always enabled
    staleTime: 30 * 1000,
  });
}

// ─── useBulkDeleteTrades ──────────────────────────────────────────────────────

export function useBulkDeleteTrades() {
  const qc = useQueryClient();
  return useMutation<void, Error, BulkDeletePayload>({
    mutationFn: async ({ trade_ids, portfolio_id }) => {
      const { error } = await bulkDeleteTradesApiV1PortfoliosPortfolioIdTradesBulkDeletePost({
        path: { portfolio_id },
        body: { trade_ids },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}

// ─── useBulkAssignTag ─────────────────────────────────────────────────────────

export function useBulkAssignTag() {
  const qc = useQueryClient();
  return useMutation<void, Error, BulkAssignTagPayload>({
    mutationFn: async ({ trade_ids, tag_ids, portfolio_id }) => {
      const { error } = await bulkAssignTagsApiV1PortfoliosPortfolioIdTradesBulkAssignTagsPost({
        path: { portfolio_id },
        body: { trade_ids, tag_ids, mode: "add" },
      });
      if (error) throw error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["trades"] }),
  });
}

// ─── useBulkAssignPlaybook ────────────────────────────────────────────────────

export function useBulkAssignPlaybook() {
  const qc = useQueryClient();
  return useMutation<void, Error, BulkAssignPlaybookPayload>({
    mutationFn: async ({ trade_ids, playbook_id, portfolio_id }) => {
      const { error } = await bulkAssignPlaybookApiV1PortfoliosPortfolioIdTradesBulkAssignPlaybookPost({
        path: { portfolio_id },
        body: { trade_ids, playbook_id },
      });
      if (error) throw error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["trades"] }),
  });
}
