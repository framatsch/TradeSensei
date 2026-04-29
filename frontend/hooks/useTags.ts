/**
 * React Query hooks for tag CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listTagsApiV1TagsGet,
  createTagApiV1TagsPost,
  deleteTagApiV1TagsTagIdDelete,
} from "@/lib/api/index";
import type {
  ResponseEnvelope,
  Tag,
  TagCreate,
} from "@/lib/types";

export function useTags() {
  return useQuery<Tag[], Error>({
    queryKey: ["tags"],
    queryFn: async () => {
      const { data, error } = await listTagsApiV1TagsGet();
      if (error || !data) throw error;
      return (data as unknown as ResponseEnvelope<Tag[]>).data;
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation<Tag, Error, TagCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createTagApiV1TagsPost({
        body: payload as import("@/lib/api/types.gen").TagCreate,
      });
      if (error || !data) throw error;
      return (data as unknown as ResponseEnvelope<Tag>).data;
    },
    onSuccess: (newTag) => {
      // Optimistic update: immediately add the new tag to the cache
      qc.setQueryData<Tag[]>(["tags"], (old) => [...(old ?? []), newTag]);
    },
    onError: () => {
      // On error, invalidate to re-fetch the real server state
      void qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await deleteTagApiV1TagsTagIdDelete({
        path: { tag_id: id },
      });
      if (error) throw error;
    },
    onSuccess: (_data, id) => {
      // Optimistic update: immediately remove the deleted tag from the cache
      qc.setQueryData<Tag[]>(["tags"], (old) =>
        (old ?? []).filter((t) => t.id !== id)
      );
    },
    onError: () => {
      // On error, invalidate to re-fetch the real server state
      void qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}
