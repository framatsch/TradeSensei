/**
 * React Query hooks for tag CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  ResponseEnvelope,
  Tag,
  TagCreate,
} from "@/lib/types";

export function useTags() {
  return useQuery<Tag[], Error>({
    queryKey: ["tags"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<Tag[]>>(
        "/api/v1/tags"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation<Tag, Error, TagCreate>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Tag>>(
        "/api/v1/tags",
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/tags/${id}`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["tags"] });
    },
  });
}
