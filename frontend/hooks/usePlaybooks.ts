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

/**
 * React Query hooks for playbook CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listPlaybooksApiV1PlaybooksGet,
  createPlaybookApiV1PlaybooksPost,
  updatePlaybookApiV1PlaybooksPlaybookIdPatch,
  deletePlaybookApiV1PlaybooksPlaybookIdDelete,
} from "@/lib/api/index";
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
      const { data, error } = await listPlaybooksApiV1PlaybooksGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as ResponseEnvelope<Playbook[]>).data;
    },
    staleTime: 60 * 1000,
  });
}

export function useCreatePlaybook() {
  const qc = useQueryClient();
  return useMutation<Playbook, Error, PlaybookCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createPlaybookApiV1PlaybooksPost({
        body: payload as import("@/lib/api/types.gen").PlaybookCreate,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as ResponseEnvelope<Playbook>).data;
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
      const { data, error } = await updatePlaybookApiV1PlaybooksPlaybookIdPatch({
        path: { playbook_id: id },
        body: payload as import("@/lib/api/types.gen").PlaybookUpdate,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as ResponseEnvelope<Playbook>).data;
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
      const { error } = await deletePlaybookApiV1PlaybooksPlaybookIdDelete({
        path: { playbook_id: id },
      });
      if (error) throw error ?? new Error("Request failed");
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
