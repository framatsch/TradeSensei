/**
 * React Query hooks for single trade fetch, create, and update.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { ResponseEnvelope, Trade, TradeCreate, TradeUpdate } from "@/lib/types";

export function useTrade(id: string) {
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useQuery<Trade, Error>({
    queryKey: ["trade", id, portfolioId],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        path: { portfolio_id: portfolioId!, trade_id: id },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 1000, // 5 seconds to ensure fresh data after execution updates
    enabled: Boolean(id) && Boolean(portfolioId),
  });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Trade, Error, TradeCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.post<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/portfolios/{portfolio_id}/trades",
        path: { portfolio_id: portfolioId! },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
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
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Trade, Error, TradeUpdate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.patch<ResponseEnvelope<Trade>, unknown, false>({
        url: "/api/v1/portfolios/{portfolio_id}/trades/{trade_id}",
        path: { portfolio_id: portfolioId!, trade_id: id },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    onSuccess: (updated) => {
      // Update the individual trade cache — key must match useTrade's queryKey
      qc.setQueryData(["trade", id, portfolioId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}
