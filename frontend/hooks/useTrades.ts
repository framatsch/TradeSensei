/**
 * React Query hooks for trade list fetching and bulk operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
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
  account_id?: string;
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
  cursor?: string | null;
  limit?: number;
  filters?: TradeFilters;
  sort?: TradeSortConfig;
}

// ─── Bulk operation payload types ────────────────────────────────────────────

interface BulkDeletePayload {
  trade_ids: string[];
}

interface BulkAssignTagPayload {
  trade_ids: string[];
  tag_ids: string[];
}

interface BulkAssignPlaybookPayload {
  trade_ids: string[];
  playbook_id: string | null;
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
  cursor,
  limit = 20,
  filters,
  sort,
}: UseTradesOptions = {}) {
  return useQuery<CursorPage<Trade>, Error>({
    queryKey: ["trades", cursor, limit, filters, sort],
    queryFn: async () => {
      // Build URLSearchParams manually to support repeated keys for arrays
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      if (cursor) params.set("cursor", cursor);

      if (filters) {
        if (filters.symbol) params.set("symbol", filters.symbol);
        if (filters.direction) params.set("direction", filters.direction);
        if (filters.asset_classes?.length) {
          for (const ac of filters.asset_classes) {
            params.append("asset_class", ac);
          }
        }
        if (filters.opened_at_from) params.set("opened_at_from", toUtcFrom(filters.opened_at_from));
        if (filters.opened_at_to) params.set("opened_at_to", toUtcTo(filters.opened_at_to));
        if (filters.closed_at_from) params.set("closed_at_from", toUtcFrom(filters.closed_at_from));
        if (filters.closed_at_to) params.set("closed_at_to", toUtcTo(filters.closed_at_to));
        if (filters.tag_ids?.length) {
          for (const tid of filters.tag_ids) {
            params.append("tag_ids", tid);
          }
          // Use OR logic so selecting multiple tags returns trades with ANY of them
          params.set("tag_filter_mode", "or");
        }
        if (filters.playbook_id) params.set("playbook_id", filters.playbook_id);
        if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) {
          params.set("pnl_positive", String(filters.pnl_positive));
        }
        if (filters.status) params.set("status", filters.status);
        if (filters.account_id) params.set("account_id", filters.account_id);
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

      const res = await apiClient.get<ResponseEnvelope<CursorPage<Trade>>>(
        `/api/v1/trades?${params.toString()}`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}

// ─── useBulkDeleteTrades ──────────────────────────────────────────────────────

export function useBulkDeleteTrades() {
  const qc = useQueryClient();
  return useMutation<void, Error, BulkDeletePayload>({
    mutationFn: async (payload) => {
      await apiClient.post("/api/v1/trades/bulk/delete", payload);
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
    mutationFn: async (payload) => {
      await apiClient.post("/api/v1/trades/bulk/assign-tags", payload);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["trades"] }),
  });
}

// ─── useBulkAssignPlaybook ────────────────────────────────────────────────────

export function useBulkAssignPlaybook() {
  const qc = useQueryClient();
  return useMutation<void, Error, BulkAssignPlaybookPayload>({
    mutationFn: async (payload) => {
      await apiClient.post("/api/v1/trades/bulk/assign-playbook", payload);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["trades"] }),
  });
}
