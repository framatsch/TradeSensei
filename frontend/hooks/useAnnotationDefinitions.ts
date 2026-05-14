"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAnnotationDefinitionApiV1AnnotationDefinitionsPost,
  deleteAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdDelete,
  listAnnotationDefinitionsApiV1AnnotationDefinitionsGet,
  updateAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdPut,
} from "@/lib/api/index";
import type {
  AnnotationDefinitionCreate,
  AnnotationDefinitionResponse,
  AnnotationDefinitionUpdate,
} from "@/lib/api/types.gen";

const QUERY_KEY = ["annotation-definitions"] as const;

export function useGetAnnotationDefinitions(scope?: "trades" | "checkins" | "both") {
  return useQuery<AnnotationDefinitionResponse[], Error>({
    queryKey: [...QUERY_KEY, scope ?? "all"],
    queryFn: async () => {
      const { data, error } = await listAnnotationDefinitionsApiV1AnnotationDefinitionsGet({
        // Omit the query param entirely when no scope is requested — passing null
        // would make the backend treat it as a filter for a null scope value.
        query: scope ? { scope } : {},
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as AnnotationDefinitionResponse[];
    },
    staleTime: 60_000,
  });
}

export function useCreateAnnotationDefinition() {
  const queryClient = useQueryClient();

  return useMutation<AnnotationDefinitionResponse, Error, AnnotationDefinitionCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createAnnotationDefinitionApiV1AnnotationDefinitionsPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as AnnotationDefinitionResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useUpdateAnnotationDefinition() {
  const queryClient = useQueryClient();

  return useMutation<AnnotationDefinitionResponse, Error, { definitionId: string; payload: AnnotationDefinitionUpdate }>({
    mutationFn: async ({ definitionId, payload }) => {
      const { data, error } = await updateAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdPut({
        path: { definition_id: definitionId },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as AnnotationDefinitionResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useDeleteAnnotationDefinition() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (definitionId) => {
      const { error } = await deleteAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdDelete({
        path: { definition_id: definitionId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
