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
 * React Query hooks for daily check-in entries.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listCheckinsApiV1CheckinsGet,
  createCheckinApiV1CheckinsPost,
  getCheckinApiV1CheckinsCheckinDateGet,
  updateCheckinApiV1CheckinsCheckinDatePatch,
  deleteCheckinApiV1CheckinsCheckinDateDelete,
} from "@/lib/api/index";
import type {
  DailyCheckinRead,
  DailyCheckinCreate,
  DailyCheckinUpdate,
  DailyCheckinListResponse,
} from "@/lib/api/types.gen";

export const CHECKINS_KEY = ["checkin", "entries"] as const;

export function useCheckinEntries(
  fromDate?: string,
  toDate?: string,
  targetIndices?: string,
  taxonomyIds?: string,
  annotationFilters?: string,
  limit = 30,
  offset?: number
) {
  return useQuery<DailyCheckinListResponse, Error>({
    queryKey: [...CHECKINS_KEY, { fromDate, toDate, targetIndices, taxonomyIds, annotationFilters, limit, offset }],
    queryFn: async () => {
      const { data, error } = await listCheckinsApiV1CheckinsGet({
        query: {
          from_date: fromDate ?? null,
          to_date: toDate ?? null,
          target_indices: targetIndices ?? null,
          taxonomy_ids: taxonomyIds ?? null,
          annotation_filters: annotationFilters ?? null,
          limit,
          offset: offset ?? null,
        },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as DailyCheckinListResponse;
    },
    staleTime: 30 * 1000,
  });
}

export function useCheckinEntry(date: string) {
  return useQuery<DailyCheckinRead | null, Error>({
    queryKey: [...CHECKINS_KEY, date],
    queryFn: async () => {
      const { data, error } = await getCheckinApiV1CheckinsCheckinDateGet({
        path: { checkin_date: date },
      });
      if (error) {
        if (error && typeof error === "object" && "status" in error && (error as { status: number }).status === 404) {
          return null;
        }
        throw error;
      }
      if (!data) return null;
      return data.data as DailyCheckinRead;
    },
    staleTime: 30 * 1000,
  });
}

export function useCreateCheckin() {
  const qc = useQueryClient();
  return useMutation<DailyCheckinRead, Error, DailyCheckinCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createCheckinApiV1CheckinsPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as DailyCheckinRead;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CHECKINS_KEY });
    },
  });
}

export function useUpdateCheckin() {
  const qc = useQueryClient();
  return useMutation<DailyCheckinRead, Error, { date: string; payload: DailyCheckinUpdate }>({
    mutationFn: async ({ date, payload }) => {
      const { data, error } = await updateCheckinApiV1CheckinsCheckinDatePatch({
        path: { checkin_date: date },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as DailyCheckinRead;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CHECKINS_KEY });
    },
  });
}

export function useDeleteCheckin() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (date) => {
      const { error } = await deleteCheckinApiV1CheckinsCheckinDateDelete({
        path: { checkin_date: date },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CHECKINS_KEY });
    },
  });
}
