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
  archiveTaxonomyApiV1TaxonomiesTaxonomyIdArchivePatch,
  createTaxonomyApiV1TaxonomiesPost,
  listTaxonomiesApiV1TaxonomiesGet,
  unarchiveTaxonomyApiV1TaxonomiesTaxonomyIdUnarchivePatch,
  updateTaxonomyApiV1TaxonomiesTaxonomyIdPut,
} from "@/lib/api/index";
import { deleteTaxonomyApiV1TaxonomiesTaxonomyIdDelete, getTaxonomyAssignmentsCountApiV1TaxonomiesTaxonomyIdAssignmentsCountGet } from "@/lib/api/sdk.gen";
import type {
  TaxonomyCreate,
  TaxonomyResponse,
  TaxonomyUpdate,
} from "@/lib/api/types.gen";

const QUERY_KEY = ["taxonomies"] as const;

export function useGetTaxonomies(
  scope?: "trades" | "checkins" | "both" | "playbook",
  showArchived?: boolean,
) {
  return useQuery<TaxonomyResponse[], Error>({
    queryKey: [...QUERY_KEY, scope ?? "all", showArchived ?? false],
    queryFn: async () => {
      const { data, error } = await listTaxonomiesApiV1TaxonomiesGet({
        query: { scope: scope ?? null, show_archived: showArchived ?? false },
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

  return useMutation<void, Error, { taxonomyId: string; force?: boolean }>({
    mutationFn: async ({ taxonomyId, force }) => {
      const { error } = await deleteTaxonomyApiV1TaxonomiesTaxonomyIdDelete({
        path: { taxonomy_id: taxonomyId },
        query: { force: force ?? false },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useArchiveTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<TaxonomyResponse, Error, { taxonomyId: string }>({
    mutationFn: async ({ taxonomyId }) => {
      const { data, error } = await archiveTaxonomyApiV1TaxonomiesTaxonomyIdArchivePatch({
        path: { taxonomy_id: taxonomyId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as TaxonomyResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useUnarchiveTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<TaxonomyResponse, Error, { taxonomyId: string }>({
    mutationFn: async ({ taxonomyId }) => {
      const { data, error } = await unarchiveTaxonomyApiV1TaxonomiesTaxonomyIdUnarchivePatch({
        path: { taxonomy_id: taxonomyId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as TaxonomyResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export async function fetchTaxonomyAssignmentCount(taxonomyId: string) {
  const { data, error } = await getTaxonomyAssignmentsCountApiV1TaxonomiesTaxonomyIdAssignmentsCountGet({
    path: { taxonomy_id: taxonomyId },
  });
  if (error || !data) throw error ?? new Error("Request failed");
  const payload = data as { data: { trade_count: number; checkin_count: number; playbook_count: number; total_count: number } };
  return payload.data;
}
