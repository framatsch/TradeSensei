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
    onSuccess: () => {
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
    onSuccess: () => {
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
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["playbooks"] });
    },
  });
}
