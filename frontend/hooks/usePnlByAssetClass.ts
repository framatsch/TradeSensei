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
 * React Query hook for PnL by asset class time-series data.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { PnlByAssetClass, ResponseEnvelope } from "@/lib/types";

export function usePnlByAssetClass() {
  return useQuery<PnlByAssetClass[], Error>({
    queryKey: ["metrics", "pnl-by-asset-class"],
    queryFn: async () => {
      const { data, error } = await client.get<ResponseEnvelope<PnlByAssetClass[]>, unknown, false>({
        url: "/api/v1/timeseries/pnl-by-asset-class",
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
