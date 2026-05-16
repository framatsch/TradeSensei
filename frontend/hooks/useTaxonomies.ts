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

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createTaxonomyApiV1TaxonomiesPost,
  deleteTaxonomyApiV1TaxonomiesTaxonomyIdDelete,
  listTaxonomiesApiV1TaxonomiesGet,
  updateTaxonomyApiV1TaxonomiesTaxonomyIdPut,
} from "@/lib/api/index";
import type {
  TaxonomyCreate,
  TaxonomyResponse,
  TaxonomyUpdate,
} from "@/lib/api/types.gen";

const QUERY_KEY = ["taxonomies"] as const;

export function useGetTaxonomies(scope?: "trades" | "checkins" | "both" | "playbook") {
  return useQuery<TaxonomyResponse[], Error>({
    queryKey: [...QUERY_KEY, scope ?? "all"],
    queryFn: async () => {
      const { data, error } = await listTaxonomiesApiV1TaxonomiesGet({
        query: { scope: scope ?? null },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as TaxonomyResponse[];
    },
    staleTime: 60_000,
  });
}

export function useCreateTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<TaxonomyResponse, Error, TaxonomyCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createTaxonomyApiV1TaxonomiesPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as TaxonomyResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useUpdateTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<TaxonomyResponse, Error, { taxonomyId: string; payload: TaxonomyUpdate }>({
    mutationFn: async ({ taxonomyId, payload }) => {
      const { data, error } = await updateTaxonomyApiV1TaxonomiesTaxonomyIdPut({
        path: { taxonomy_id: taxonomyId },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as TaxonomyResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useDeleteTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (taxonomyId) => {
      const { error } = await deleteTaxonomyApiV1TaxonomiesTaxonomyIdDelete({
        path: { taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
