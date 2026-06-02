/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
      const pathPart = url.split("?")[0];
      const filename = pathPart.split("/").pop()!;
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
