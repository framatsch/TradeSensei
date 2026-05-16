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
