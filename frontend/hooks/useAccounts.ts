/**
 * React Query hook for the user's broker accounts list.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { Account, CursorPage, ResponseEnvelope } from "@/lib/types";

export function useAccounts() {
  return useQuery<Account[], Error>({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<CursorPage<Account>>>(
        "/api/v1/accounts"
      );
      return res.data.data.items;
    },
    staleTime: 5 * 60 * 1000,
  });
}
