/**
 * React Query hook for merging multiple trades into one.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deprecatedTradesApiV1TradesMergePost } from "@/lib/api/index";
import type { MergeTradesRequest, Trade } from "@/lib/types";

/** Merge two or more trades into a single surviving trade. */
export function useMergeTrades() {
  const qc = useQueryClient();
  return useMutation<Trade, Error, MergeTradesRequest>({
    mutationFn: async (payload) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await deprecatedTradesApiV1TradesMergePost({ body: payload as any });
      if (error || !data) throw error;
      // Deprecated endpoint returns unknown — cast to expected shape
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return ((data as any).data ?? data) as Trade;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
