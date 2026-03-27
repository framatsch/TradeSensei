/**
 * React Query hooks for playbook CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  Playbook,
  PlaybookCreate,
  PlaybookUpdate,
  ResponseEnvelope,
} from "@/lib/types";

export function usePlaybooks() {
  return useQuery<Playbook[], Error>({
    queryKey: ["playbooks"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<Playbook[]>>(
        "/api/v1/playbooks"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}

export function useCreatePlaybook() {
  const qc = useQueryClient();
  return useMutation<Playbook, Error, PlaybookCreate>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Playbook>>(
        "/api/v1/playbooks",
        payload
      );
      return res.data.data;
    },
    onSuccess: (newPlaybook) => {
      // Optimistic update: immediately add the new playbook to the cache
      qc.setQueryData<Playbook[]>(["playbooks"], (old) => [
        ...(old ?? []),
        newPlaybook,
      ]);
    },
    onError: () => {
      // On error, invalidate to re-fetch the real server state
      void qc.invalidateQueries({ queryKey: ["playbooks"] });
    },
  });
}

export function useUpdatePlaybook() {
  const qc = useQueryClient();
  return useMutation<Playbook, Error, { id: string; payload: PlaybookUpdate }>({
    mutationFn: async ({ id, payload }) => {
      const res = await apiClient.patch<ResponseEnvelope<Playbook>>(
        `/api/v1/playbooks/${id}`,
        payload
      );
      return res.data.data;
    },
    onSuccess: (updated) => {
      // Immediately replace the updated playbook in the cache
      qc.setQueryData<Playbook[]>(["playbooks"], (old) =>
        (old ?? []).map((pb) => (pb.id === updated.id ? updated : pb))
      );
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: ["playbooks"] });
    },
  });
}

export function useDeletePlaybook() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/playbooks/${id}`);
    },
    onSuccess: (_data, deletedId) => {
      // Immediately remove the deleted playbook from the cache
      qc.setQueryData<Playbook[]>(["playbooks"], (old) =>
        (old ?? []).filter((pb) => pb.id !== deletedId)
      );
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: ["playbooks"] });
    },
  });
}
