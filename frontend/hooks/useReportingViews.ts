/**
 * React Query hooks for saved dashboard view CRUD operations.
 *
 * Saved dashboard views persist a filter configuration so users can
 * quickly switch between different analytics perspectives.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listSavedDashboardViewsApiV1PortfoliosPortfolioIdViewsGet,
  createSavedDashboardViewApiV1PortfoliosPortfolioIdViewsPost,
  updateSavedDashboardViewApiV1PortfoliosPortfolioIdViewsViewIdPatch,
  deleteSavedDashboardViewApiV1PortfoliosPortfolioIdViewsViewIdDelete,
} from "@/lib/api";
import type {
  SavedDashboardViewRead,
  SavedDashboardViewCreate,
  SavedDashboardViewUpdate,
} from "@/lib/api/types.gen";

// ─── Query key factory ────────────────────────────────────────────────────────

function viewsQueryKey(portfolioId: string | null) {
  return ["saved-dashboard-views", portfolioId] as const;
}

// ─── List views ───────────────────────────────────────────────────────────────

export function useSavedViews(portfolioId: string | null) {
  return useQuery<SavedDashboardViewRead[], Error>({
    queryKey: viewsQueryKey(portfolioId),
    queryFn: async () => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await listSavedDashboardViewsApiV1PortfoliosPortfolioIdViewsGet({
          path: { portfolio_id: portfolioId },
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    staleTime: 60 * 1000,
    enabled: !!portfolioId,
  });
}

// ─── Create view ──────────────────────────────────────────────────────────────

export function useSaveView(portfolioId: string | null) {
  const qc = useQueryClient();

  return useMutation<SavedDashboardViewRead, Error, SavedDashboardViewCreate>({
    mutationFn: async (payload) => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await createSavedDashboardViewApiV1PortfoliosPortfolioIdViewsPost({
          path: { portfolio_id: portfolioId },
          body: payload,
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: viewsQueryKey(portfolioId) });
    },
  });
}

// ─── Update view ──────────────────────────────────────────────────────────────

export function useUpdateView(portfolioId: string | null) {
  const qc = useQueryClient();

  return useMutation<
    SavedDashboardViewRead,
    Error,
    { viewId: string; payload: SavedDashboardViewUpdate }
  >({
    mutationFn: async ({ viewId, payload }) => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { data, error } =
        await updateSavedDashboardViewApiV1PortfoliosPortfolioIdViewsViewIdPatch({
          path: { portfolio_id: portfolioId, view_id: viewId },
          body: payload,
        });

      if (error || !data) {
        throw error ?? new Error("Request failed: no data returned");
      }
      return data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: viewsQueryKey(portfolioId) });
    },
  });
}

// ─── Delete view ──────────────────────────────────────────────────────────────

export function useDeleteView(portfolioId: string | null) {
  const qc = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (viewId) => {
      if (!portfolioId) throw new Error("No portfolio selected");

      const { error } =
        await deleteSavedDashboardViewApiV1PortfoliosPortfolioIdViewsViewIdDelete({
          path: { portfolio_id: portfolioId, view_id: viewId },
        });

      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: viewsQueryKey(portfolioId) });
    },
  });
}