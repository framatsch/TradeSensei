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
