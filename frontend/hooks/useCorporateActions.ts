/**
 * React Query hooks for corporate action CRUD operations.
 *
 * Corporate actions (stock splits / reverse splits) are used by the import
 * service to adjust trade quantities and prices when a split event occurred
 * during the lifetime of an open position.
 *
 * The `ratio` field follows the convention: `after_shares / before_shares`.
 * - Forward split 2:1  → ratio = "2.0"
 * - Reverse split 1:20 → ratio = "0.05"
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  CorporateAction,
  CorporateActionCreate,
  CorporateActionUpdate,
  ResponseEnvelope,
} from "@/lib/types";

const QUERY_KEY = ["corporate-actions"] as const;

/**
 * Fetch all corporate actions owned by the authenticated user.
 * Results are ordered by date ascending.
 */
export function useListCorporateActions() {
  return useQuery<CorporateAction[], Error>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<CorporateAction[]>>(
        "/api/v1/corporate-actions"
      );
      return res.data.data;
    },
    staleTime: 60 * 1000,
  });
}

/**
 * Create a new corporate action.
 * The `ratio` should be supplied as a decimal string computed as
 * `after / before` (e.g. `"0.05"` for a 1:20 reverse split).
 */
export function useCreateCorporateAction() {
  const qc = useQueryClient();
  return useMutation<CorporateAction, Error, CorporateActionCreate>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<CorporateAction>>(
        "/api/v1/corporate-actions",
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Partially update an existing corporate action.
 * Only the fields present in the payload are changed.
 */
export function useUpdateCorporateAction() {
  const qc = useQueryClient();
  return useMutation<
    CorporateAction,
    Error,
    { id: string; payload: CorporateActionUpdate }
  >({
    mutationFn: async ({ id, payload }) => {
      const res = await apiClient.put<ResponseEnvelope<CorporateAction>>(
        `/api/v1/corporate-actions/${id}`,
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Delete a corporate action by ID.
 */
export function useDeleteCorporateAction() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/corporate-actions/${id}`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
