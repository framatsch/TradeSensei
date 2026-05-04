/**
 * React Query hooks for check-in configuration entities.
 *
 * MarketPhaseDefinition  — CRU (no delete; deactivation via is_active)
 * CheckinFieldDefinition  — CRU (no delete; deactivation via is_active)
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listMarketPhasesApiV1MarketPhasesGet,
  createMarketPhaseApiV1MarketPhasesPost,
  updateMarketPhaseApiV1MarketPhasesPhaseIdPatch,
  listMarketIndexesApiV1MarketIndexesGet,
  createMarketIndexApiV1MarketIndexesPost,
  updateMarketIndexApiV1MarketIndexesIndexIdPut,
  deleteMarketIndexApiV1MarketIndexesIndexIdDelete,
  listCheckinFieldsApiV1CheckinFieldsGet,
  createCheckinFieldApiV1CheckinFieldsPost,
  updateCheckinFieldApiV1CheckinFieldsFieldIdPatch,
} from "@/lib/api/index";
import type {
  MarketIndexDefinitionResponse,
  MarketIndexDefinitionCreate,
  MarketIndexDefinitionUpdate,
  MarketPhaseDefinitionRead,
  MarketPhaseDefinitionCreate,
  MarketPhaseDefinitionUpdate,
  CheckinFieldDefinitionRead,
  CheckinFieldDefinitionCreate,
  CheckinFieldDefinitionUpdate,
} from "@/lib/api/types.gen";

export const MARKET_PHASES_KEY = ["checkin", "market-phases"] as const;
export const MARKET_INDEXES_KEY = ["checkin", "market-indexes"] as const;
export const CHECKIN_FIELDS_KEY = ["checkin", "fields"] as const;

// ─── Market Indexes ──────────────────────────────────────────────────────────

export function useMarketIndexes() {
  return useQuery<MarketIndexDefinitionResponse[], Error>({
    queryKey: MARKET_INDEXES_KEY,
    queryFn: async () => {
      const { data, error } = await listMarketIndexesApiV1MarketIndexesGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse[];
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateMarketIndex() {
  const qc = useQueryClient();
  return useMutation<MarketIndexDefinitionResponse, Error, MarketIndexDefinitionCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createMarketIndexApiV1MarketIndexesPost({
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}

export function useUpdateMarketIndex() {
  const qc = useQueryClient();
  return useMutation<
    MarketIndexDefinitionResponse,
    Error,
    { id: string; payload: MarketIndexDefinitionUpdate }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data, error } = await updateMarketIndexApiV1MarketIndexesIndexIdPut({
        path: { index_id: id },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketIndexDefinitionResponse;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}

export function useDeleteMarketIndex() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await deleteMarketIndexApiV1MarketIndexesIndexIdDelete({
        path: { index_id: id },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MARKET_INDEXES_KEY });
    },
  });
}

// ─── Market Phases ────────────────────────────────────────────────────────────

export function useMarketPhases() {
  return useQuery<MarketPhaseDefinitionRead[], Error>({
    queryKey: MARKET_PHASES_KEY,
    queryFn: async () => {
      const { data, error } = await listMarketPhasesApiV1MarketPhasesGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketPhaseDefinitionRead[];
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateMarketPhase() {
  const qc = useQueryClient();
  return useMutation<MarketPhaseDefinitionRead, Error, MarketPhaseDefinitionCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createMarketPhaseApiV1MarketPhasesPost({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: payload as any,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketPhaseDefinitionRead;
    },
    onSuccess: (newPhase) => {
      qc.setQueryData<MarketPhaseDefinitionRead[]>(MARKET_PHASES_KEY, (old) => [...(old ?? []), newPhase]);
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: MARKET_PHASES_KEY });
    },
  });
}

export function useUpdateMarketPhase() {
  const qc = useQueryClient();
  return useMutation<
    MarketPhaseDefinitionRead,
    Error,
    { id: string; payload: MarketPhaseDefinitionUpdate }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data, error } = await updateMarketPhaseApiV1MarketPhasesPhaseIdPatch({
        path: { phase_id: id },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: payload as any,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as MarketPhaseDefinitionRead;
    },
    onSuccess: (updated) => {
      qc.setQueryData<MarketPhaseDefinitionRead[]>(MARKET_PHASES_KEY, (old) =>
        (old ?? []).map((p) => (p.id === updated.id ? updated : p))
      );
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: MARKET_PHASES_KEY });
    },
  });
}

// ─── Check-in Fields ──────────────────────────────────────────────────────────

export function useCheckinFields() {
  return useQuery<CheckinFieldDefinitionRead[], Error>({
    queryKey: CHECKIN_FIELDS_KEY,
    queryFn: async () => {
      const { data, error } = await listCheckinFieldsApiV1CheckinFieldsGet();
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CheckinFieldDefinitionRead[];
    },
    staleTime: 60 * 1000,
  });
}

export function useCreateCheckinField() {
  const qc = useQueryClient();
  return useMutation<CheckinFieldDefinitionRead, Error, CheckinFieldDefinitionCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createCheckinFieldApiV1CheckinFieldsPost({
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: payload as any,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CheckinFieldDefinitionRead;
    },
    onSuccess: (newField) => {
      qc.setQueryData<CheckinFieldDefinitionRead[]>(CHECKIN_FIELDS_KEY, (old) => [...(old ?? []), newField]);
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: CHECKIN_FIELDS_KEY });
    },
  });
}

export function useUpdateCheckinField() {
  const qc = useQueryClient();
  return useMutation<
    CheckinFieldDefinitionRead,
    Error,
    { id: string; payload: CheckinFieldDefinitionUpdate }
  >({
    mutationFn: async ({ id, payload }) => {
      const { data, error } = await updateCheckinFieldApiV1CheckinFieldsFieldIdPatch({
        path: { field_id: id },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        body: payload as any,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as CheckinFieldDefinitionRead;
    },
    onSuccess: (updated) => {
      qc.setQueryData<CheckinFieldDefinitionRead[]>(CHECKIN_FIELDS_KEY, (old) =>
        (old ?? []).map((f) => (f.id === updated.id ? updated : f))
      );
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: CHECKIN_FIELDS_KEY });
    },
  });
}
