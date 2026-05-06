/**
 * React Query mutation hook for IBKR Flex Query import.
 */

"use client";

import { useMutation } from "@tanstack/react-query";
import { flexImportApiV1PortfoliosPortfolioIdImportsFlexPost } from "@/lib/api/index";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { ImportResult } from "@/lib/types";

interface FlexImportPayload {
  query_id: string;
  from_date?: string | null;
}

export function useFlexImport() {
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);

  return useMutation<ImportResult, Error, FlexImportPayload>({
    mutationFn: async (payload) => {
      if (!portfolioId) throw new Error("No active portfolio");

      const { data, error } = await flexImportApiV1PortfoliosPortfolioIdImportsFlexPost({
        path: { portfolio_id: portfolioId },
        body: {
          query_id: payload.query_id,
          from_date: payload.from_date ?? undefined,
        },
      });

      if (error || !data) {
        throw error ?? new Error("Flex import failed");
      }

      // Die SDK-Funktion gibt bei uns ResponseEnvelope zurück, also data.data
      return (data as any).data as ImportResult;
    },
  });
}
