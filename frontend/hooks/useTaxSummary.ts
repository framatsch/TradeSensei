/**
 * React Query hook for the annual tax summary endpoint.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import type { TaxAnnualSummary } from "@/lib/types";
import { getAnnualSummaryApiV1TaxAnnualSummaryGet } from "@/lib/api/index";

export function useTaxSummary(year: number) {
  return useQuery<TaxAnnualSummary, Error>({
    queryKey: ["tax", "annual-summary", year],
    queryFn: async () => {
      const { data, error } = await getAnnualSummaryApiV1TaxAnnualSummaryGet({
        query: { year },
      });
      if (error || !data) throw error;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as TaxAnnualSummary;
    },
    staleTime: 5 * 60 * 1000,
  });
}
