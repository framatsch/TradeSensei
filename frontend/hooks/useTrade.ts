/**
 * React Query hooks for single trade fetch, create, and update.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ResponseEnvelope, Trade, TradeCreate, TradeUpdate } from "@/lib/types";

export function useTrade(id: string) {
  return useQuery<Trade, Error>({
    queryKey: ["trade", id],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${id}`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
    enabled: Boolean(id),
  });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  return useMutation<Trade, Error, TradeCreate>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Trade>>(
        "/api/v1/trades",
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function useUpdateTrade(id: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, TradeUpdate>({
    mutationFn: async (payload) => {
      const res = await apiClient.patch<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${id}`,
        payload
      );
      return res.data.data;
    },
    onSuccess: (updated) => {
      // Update the individual trade cache and invalidate the list
      qc.setQueryData(["trade", id], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function usePartialCloseTrade(id: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, import("@/lib/types").TradePartialCloseRequest>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${id}/partial-close`,
        payload
      );
      return res.data.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", id], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
