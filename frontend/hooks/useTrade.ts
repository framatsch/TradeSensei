/**
 * React Query hooks for single trade fetch, create, and update.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { ResponseEnvelope, Trade, TradeCreate, TradeUpdate } from "@/lib/types";

export function useTrade(id: string) {
  return useQuery<Trade, Error>({
    queryKey: ["trade", id],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/trades/{trade_id}",
        path: { trade_id: id },
      });
      if (error || !data) throw error;
      return data.data;
    },
    staleTime: 5 * 1000, // 5 seconds to ensure fresh data after execution updates
    enabled: Boolean(id),
  });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  return useMutation<Trade, Error, TradeCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.post<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/trades",
        body: payload,
      });
      if (error || !data) throw error;
      return data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}

export function useUpdateTrade(id: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, TradeUpdate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.patch<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/trades/{trade_id}",
        path: { trade_id: id },
        body: payload,
      });
      if (error || !data) throw error;
      return data.data;
    },
    onSuccess: (updated) => {
      // Update the individual trade cache and invalidate the list
      qc.setQueryData(["trade", id], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}
