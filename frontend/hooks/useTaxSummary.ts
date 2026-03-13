/**
 * React Query hook for the annual tax summary endpoint.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { TaxAnnualSummary, ResponseEnvelope } from "@/lib/types";

export function useTaxSummary(year: number) {
  return useQuery<TaxAnnualSummary, Error>({
    queryKey: ["tax", "annual-summary", year],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<TaxAnnualSummary>>(
        "/api/v1/tax/annual-summary",
        { params: { year } }
      );
      return res.data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
