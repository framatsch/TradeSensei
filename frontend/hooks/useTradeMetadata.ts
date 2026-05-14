"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  assignTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdPost,
  assignTradeTaxonomyApiV1TradesTradeIdTaxonomiesPost,
  removeTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdDelete,
  removeTradeTaxonomyApiV1TradesTradeIdTaxonomiesTaxonomyIdDelete,
  updateTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdPut,
} from "@/lib/api/index";
import type { AnnotationAssignRequest } from "@/lib/api/types.gen";

export function useAssignTradeTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { tradeId: string; taxonomyId: string; portfolioId?: string }>({
    mutationFn: async ({ tradeId, taxonomyId }) => {
      const { error } = await assignTradeTaxonomyApiV1TradesTradeIdTaxonomiesPost({
        path: { trade_id: tradeId },
        body: { taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["trade", variables.tradeId, variables.portfolioId ?? ""] });
    },
  });
}

export function useRemoveTradeTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { tradeId: string; taxonomyId: string; portfolioId?: string }>({
    mutationFn: async ({ tradeId, taxonomyId }) => {
      const { error } = await removeTradeTaxonomyApiV1TradesTradeIdTaxonomiesTaxonomyIdDelete({
        path: { trade_id: tradeId, taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["trade", variables.tradeId, variables.portfolioId ?? ""] });
    },
  });
}

export function useAssignTradeAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { tradeId: string; annotationDefinitionId: string; value: AnnotationAssignRequest["value"]; portfolioId?: string }
  >({
    mutationFn: async ({ tradeId, annotationDefinitionId, value }) => {
      const { error } = await assignTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdPost({
        path: {
          trade_id: tradeId,
          annotation_definition_id: annotationDefinitionId,
        },
        body: { value },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["trade", variables.tradeId, variables.portfolioId ?? ""] });
    },
  });
}

export function useUpdateTradeAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { tradeId: string; annotationDefinitionId: string; value: AnnotationAssignRequest["value"]; portfolioId?: string }
  >({
    mutationFn: async ({ tradeId, annotationDefinitionId, value }) => {
      const { error } = await updateTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdPut({
        path: {
          trade_id: tradeId,
          annotation_definition_id: annotationDefinitionId,
        },
        body: { value },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["trade", variables.tradeId, variables.portfolioId ?? ""] });
    },
  });
}

export function useRemoveTradeAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { tradeId: string; annotationDefinitionId: string; portfolioId?: string }>({
    mutationFn: async ({ tradeId, annotationDefinitionId }) => {
      const { error } = await removeTradeAnnotationApiV1TradesTradeIdAnnotationsAnnotationDefinitionIdDelete({
        path: {
          trade_id: tradeId,
          annotation_definition_id: annotationDefinitionId,
        },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["trade", variables.tradeId, variables.portfolioId ?? ""] });
    },
  });
}
