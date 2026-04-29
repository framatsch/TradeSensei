/**
 * React Query hooks for screenshot upload and deletion.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  uploadScreenshotApiV1TradesTradeIdScreenshotsPost,
  deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete,
} from "@/lib/api/index";
import type { Trade } from "@/lib/types";

export function useUploadScreenshot(tradeId: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, File>({
    mutationFn: async (file: File) => {
      const { data, error } = await uploadScreenshotApiV1TradesTradeIdScreenshotsPost({
        path: { trade_id: tradeId },
        body: { file },
      });
      if (error || !data) throw error;
      return data.data as unknown as Trade;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", tradeId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function useDeleteScreenshot(tradeId: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, string>({
    mutationFn: async (url: string) => {
      // Extract only the filename from the full URL path
      const filename = url.split("/").pop()!;
      const { data, error } = await deleteScreenshotApiV1TradesTradeIdScreenshotsFilenameDelete({
        path: { trade_id: tradeId, filename },
      });
      if (error || !data) throw error;
      return data.data as unknown as Trade;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", tradeId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
