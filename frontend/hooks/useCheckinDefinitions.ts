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
 * React Query hooks for check-in configuration entities.
 *
 * MarketIndexDefinition — CRU + delete
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listMarketIndexesApiV1MarketIndexesGet,
  createMarketIndexApiV1MarketIndexesPost,
  updateMarketIndexApiV1MarketIndexesIndexIdPut,
  deleteMarketIndexApiV1MarketIndexesIndexIdDelete,
} from "@/lib/api/index";
import type {
  MarketIndexDefinitionResponse,
  MarketIndexDefinitionCreate,
  MarketIndexDefinitionUpdate,
} from "@/lib/api/types.gen";

export const MARKET_INDEXES_KEY = ["checkin", "market-indexes"] as const;

// ─── Market Indexes ──────────────────────────────────────────────────────────

export function useMarketIndexes() {
  return useQuery<MarketIndexDefinitionResponse[], Error>({
    queryKey: MARKET_INDEXES_KEY,
    queryFn: async () => {
      const { data, error } = await listMarketIndexesApiV1MarketIndexesGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse[];
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateMarketIndex() {
  const qc = useQueryClient();
  return useMutation<MarketIndexDefinitionResponse, Error, MarketIndexDefinitionCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createMarketIndexApiV1MarketIndexesPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}

export function useUpdateMarketIndex() {
  const qc = useQueryClient();
  return useMutation<
    MarketIndexDefinitionResponse,
    Error,
    { id: string; payload: MarketIndexDefinitionUpdate }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data, error } = await updateMarketIndexApiV1MarketIndexesIndexIdPut({
        path: { index_id: id },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}

export function useDeleteMarketIndex() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await deleteMarketIndexApiV1MarketIndexesIndexIdDelete({
        path: { index_id: id },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}
