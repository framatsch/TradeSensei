/**
 * React Query hooks for screenshot upload and deletion.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ResponseEnvelope, Trade } from "@/lib/types";

export function useUploadScreenshot(tradeId: string) {
  const qc = useQueryClient();
  return useMutation<Trade, Error, File>({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await apiClient.post<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${tradeId}/screenshots`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return res.data.data;
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
      const res = await apiClient.delete<ResponseEnvelope<Trade>>(
        `/api/v1/trades/${tradeId}/screenshots/${filename}`
      );
      return res.data.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["trade", tradeId], updated);
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
