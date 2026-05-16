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
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as TaxAnnualSummary;
    },
    staleTime: 5 * 60 * 1000,
  });
}
