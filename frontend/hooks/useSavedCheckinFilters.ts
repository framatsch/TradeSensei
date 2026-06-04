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
  listSavedCheckinFiltersApiV1CheckinsFiltersGet,
  createSavedCheckinFilterApiV1CheckinsFiltersPost,
  updateSavedCheckinFilterApiV1CheckinsFiltersFilterIdPut,
  deleteSavedCheckinFilterApiV1CheckinsFiltersFilterIdDelete,
} from "@/lib/api/index";
import type {
  SavedCheckinFilterCreate,
  SavedCheckinFilterUpdate,
  SavedCheckinFilterResponse,
} from "@/lib/api/types.gen";

export const SAVED_CHECKIN_FILTERS_KEY = ["saved-checkin-filters"];

export function useSavedCheckinFilters() {
  return useQuery<SavedCheckinFilterResponse[], Error>({
    queryKey: SAVED_CHECKIN_FILTERS_KEY,
    queryFn: async () => {
      const { data, error } = await listSavedCheckinFiltersApiV1CheckinsFiltersGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as SavedCheckinFilterResponse[];
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateSavedCheckinFilter() {
  const qc = useQueryClient();
  return useMutation<SavedCheckinFilterResponse, Error, SavedCheckinFilterCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createSavedCheckinFilterApiV1CheckinsFiltersPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as SavedCheckinFilterResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SAVED_CHECKIN_FILTERS_KEY });
    },
  });
}

export function useUpdateSavedCheckinFilter() {
  const qc = useQueryClient();
  return useMutation<SavedCheckinFilterResponse, Error, { id: string; payload: SavedCheckinFilterUpdate }>({
    mutationFn: async ({ id, payload }) => {
      const { data, error } = await updateSavedCheckinFilterApiV1CheckinsFiltersFilterIdPut({
        path: { filter_id: id },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as SavedCheckinFilterResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SAVED_CHECKIN_FILTERS_KEY });
    },
  });
}

export function useDeleteSavedCheckinFilter() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await deleteSavedCheckinFilterApiV1CheckinsFiltersFilterIdDelete({
        path: { filter_id: id },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SAVED_CHECKIN_FILTERS_KEY });
    },
  });
}
