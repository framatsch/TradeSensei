"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  assignCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdPost,
  assignCheckinTaxonomyApiV1CheckinsCheckinIdTaxonomiesPost,
  removeCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdDelete,
  removeCheckinTaxonomyApiV1CheckinsCheckinIdTaxonomiesTaxonomyIdDelete,
  updateCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdPut,
} from "@/lib/api/index";
import type { AnnotationAssignRequest } from "@/lib/api/types.gen";

export function useAssignCheckinTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { checkinId: string; taxonomyId: string }>({
    mutationFn: async ({ checkinId, taxonomyId }) => {
      const { error } = await assignCheckinTaxonomyApiV1CheckinsCheckinIdTaxonomiesPost({
        path: { checkin_id: checkinId },
        body: { taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries", variables.checkinId] });
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries"] });
    },
  });
}

export function useRemoveCheckinTaxonomy() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { checkinId: string; taxonomyId: string }>({
    mutationFn: async ({ checkinId, taxonomyId }) => {
      const { error } = await removeCheckinTaxonomyApiV1CheckinsCheckinIdTaxonomiesTaxonomyIdDelete({
        path: { checkin_id: checkinId, taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries", variables.checkinId] });
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries"] });
    },
  });
}

export function useAssignCheckinAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { checkinId: string; annotationDefinitionId: string; value: AnnotationAssignRequest["value"] }
  >({
    mutationFn: async ({ checkinId, annotationDefinitionId, value }) => {
      const { error } = await assignCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdPost({
        path: {
          checkin_id: checkinId,
          annotation_definition_id: annotationDefinitionId,
        },
        body: { value },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries", variables.checkinId] });
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries"] });
    },
  });
}

export function useUpdateCheckinAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { checkinId: string; annotationDefinitionId: string; value: AnnotationAssignRequest["value"] }
  >({
    mutationFn: async ({ checkinId, annotationDefinitionId, value }) => {
      const { error } = await updateCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdPut({
        path: {
          checkin_id: checkinId,
          annotation_definition_id: annotationDefinitionId,
        },
        body: { value },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries", variables.checkinId] });
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries"] });
    },
  });
}

export function useRemoveCheckinAnnotation() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { checkinId: string; annotationDefinitionId: string }>({
    mutationFn: async ({ checkinId, annotationDefinitionId }) => {
      const { error } = await removeCheckinAnnotationApiV1CheckinsCheckinIdAnnotationsAnnotationDefinitionIdDelete({
        path: {
          checkin_id: checkinId,
          annotation_definition_id: annotationDefinitionId,
        },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries", variables.checkinId] });
      void queryClient.invalidateQueries({ queryKey: ["checkin", "entries"] });
    },
  });
}
