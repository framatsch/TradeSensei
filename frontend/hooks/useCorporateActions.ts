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
import {
  listCorporateActionsApiV1CorporateActionsGet,
  createCorporateActionApiV1CorporateActionsPost,
  updateCorporateActionApiV1CorporateActionsCorporateActionIdPut,
  deleteCorporateActionApiV1CorporateActionsCorporateActionIdDelete,
} from "@/lib/api/index";
import type {
  CorporateAction,
  CorporateActionCreate,
  CorporateActionUpdate,
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
      const { data, error } = await listCorporateActionsApiV1CorporateActionsGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CorporateAction[];
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await createCorporateActionApiV1CorporateActionsPost({ body: payload as any });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CorporateAction;
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await updateCorporateActionApiV1CorporateActionsCorporateActionIdPut({ path: { corporate_action_id: id }, body: payload as any });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CorporateAction;
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
      const { error } = await deleteCorporateActionApiV1CorporateActionsCorporateActionIdDelete({ path: { corporate_action_id: id } });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
