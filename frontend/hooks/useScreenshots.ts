/**
 * React Query hooks for screenshot upload and deletion.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  uploadScreenshotApiV1TradesTradeIdScreenshotsPost,
  deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete,
} from "@/lib/api/index";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { Trade } from "@/lib/types";

export function useUploadScreenshot(tradeId: string) {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Trade, Error, File>({
    mutationFn: async (file: File) => {
      const { data, error } = await uploadScreenshotApiV1TradesTradeIdScreenshotsPost({
        path: { trade_id: tradeId },
        body: { file },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as unknown as Trade;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", tradeId, portfolioId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function useDeleteScreenshot(tradeId: string) {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Trade, Error, string>({
    mutationFn: async (url: string) => {
      // Extract only the filename from the full URL path
      const filename = url.split("/").pop()!;
      const { data, error } = await deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete({
        path: { trade_id: tradeId, filename },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as unknown as Trade;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", tradeId, portfolioId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
