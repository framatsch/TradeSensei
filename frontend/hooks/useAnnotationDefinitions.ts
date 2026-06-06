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
  archiveAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdArchivePatch,
  createAnnotationDefinitionApiV1AnnotationDefinitionsPost,
  listAnnotationDefinitionsApiV1AnnotationDefinitionsGet,
  unarchiveAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdUnarchivePatch,
  updateAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdPut,
} from "@/lib/api/index";
import { deleteAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdDelete, getAnnotationDefinitionAssignmentsCountApiV1AnnotationDefinitionsDefinitionIdAssignmentsCountGet } from "@/lib/api/sdk.gen";
import type {
  AnnotationDefinitionCreate,
  AnnotationDefinitionResponse,
  AnnotationDefinitionUpdate,
} from "@/lib/api/types.gen";

const QUERY_KEY = ["annotation-definitions"] as const;

export function useGetAnnotationDefinitions(
  scope?: "trades" | "checkins" | "both",
  showArchived?: boolean,
) {
  return useQuery<AnnotationDefinitionResponse[], Error>({
    queryKey: [...QUERY_KEY, scope ?? "all", showArchived ?? false],
    queryFn: async () => {
      const { data, error } = await listAnnotationDefinitionsApiV1AnnotationDefinitionsGet({
        query: {
          ...(scope ? { scope } : {}),
          show_archived: showArchived ?? false,
        },
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

  return useMutation<void, Error, { definitionId: string; force?: boolean }>({
    mutationFn: async ({ definitionId, force }) => {
      const { error } = await deleteAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdDelete({
        path: { definition_id: definitionId },
        query: { force: force ?? false },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useArchiveAnnotationDefinition() {
  const queryClient = useQueryClient();

  return useMutation<AnnotationDefinitionResponse, Error, { definitionId: string }>({
    mutationFn: async ({ definitionId }) => {
      const { data, error } = await archiveAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdArchivePatch({
        path: { definition_id: definitionId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as AnnotationDefinitionResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useUnarchiveAnnotationDefinition() {
  const queryClient = useQueryClient();

  return useMutation<AnnotationDefinitionResponse, Error, { definitionId: string }>({
    mutationFn: async ({ definitionId }) => {
      const { data, error } = await unarchiveAnnotationDefinitionApiV1AnnotationDefinitionsDefinitionIdUnarchivePatch({
        path: { definition_id: definitionId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as AnnotationDefinitionResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export async function fetchAnnotationDefinitionAssignmentCount(definitionId: string) {
  const { data, error } = await getAnnotationDefinitionAssignmentsCountApiV1AnnotationDefinitionsDefinitionIdAssignmentsCountGet({
    path: { definition_id: definitionId },
  });
  if (error || !data) throw error ?? new Error("Request failed");
  const payload = data as { data: { trade_count: number; checkin_count: number; total_count: number } };
  return payload.data;
}
