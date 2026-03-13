/**
 * React Query hook for paginated trade list.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { CursorPage, ResponseEnvelope, Trade } from "@/lib/types";

interface UseTradesOptions {
  cursor?: string | null;
  limit?: number;
}

export function useTrades({ cursor, limit = 20 }: UseTradesOptions = {}) {
  return useQuery<CursorPage<Trade>, Error>({
    queryKey: ["trades", cursor, limit],
    queryFn: async () => {
      const params: Record<string, string | number> = { limit };
      if (cursor) {
        params.cursor = cursor;
      }
      const res = await apiClient.get<ResponseEnvelope<CursorPage<Trade>>>(
        "/api/v1/trades",
        { params }
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}
