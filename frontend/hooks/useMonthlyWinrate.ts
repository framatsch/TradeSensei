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
 * React Query hook for monthly win-rate data from GET /timeseries/monthly-winrate.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { ResponseEnvelope } from "@/lib/types";

export interface MonthlyWinratePoint {
  year: number;
  month: number;
  label: string;
  win_rate: string;
  win_count: number;
  loss_count: number;
  trade_count: number;
}

export function useMonthlyWinrate(accountId?: string) {
  const params = new URLSearchParams();
  if (accountId) params.set("account_id", accountId);
  const qs = params.toString() ? `?${params.toString()}` : "";

  return useQuery<MonthlyWinratePoint[], Error>({
    queryKey: ["metrics", "monthly-winrate", accountId],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<MonthlyWinratePoint[]>, unknown, false>({
        url: `/api/v1/timeseries/monthly-winrate${qs}`,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
