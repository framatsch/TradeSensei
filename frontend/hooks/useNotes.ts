/**
 * React Query hooks for trade notes CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  ResponseEnvelope,
  TradeNote,
  TradeNoteCreate,
  TradeNoteUpdate,
} from "@/lib/types";

export function useNotes(tradeId: string) {
  return useQuery<TradeNote[], Error>({
    queryKey: ["notes", tradeId],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<TradeNote[]>>(
        `/api/v1/trades/${tradeId}/notes`
      );
      return res.data?.data ?? [];
    },
    staleTime: 30 * 1000,
    enabled: Boolean(tradeId),
  });
}

export function useAddNote() {
  const qc = useQueryClient();
  return useMutation<TradeNote, Error, { tradeId: string; payload: TradeNoteCreate }>({
    mutationFn: async ({ tradeId, payload }) => {
      const res = await apiClient.post<ResponseEnvelope<TradeNote>>(
        `/api/v1/trades/${tradeId}/notes`,
        payload
      );
      return res.data.data;
    },
    onSuccess: (_data, { tradeId }) => {
      void qc.invalidateQueries({ queryKey: ["notes", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

export function useUpdateNote() {
  const qc = useQueryClient();
  return useMutation<TradeNote, Error, { tradeId: string; noteId: string; payload: TradeNoteUpdate }>({
    mutationFn: async ({ tradeId, noteId, payload }) => {
      const res = await apiClient.patch<ResponseEnvelope<TradeNote>>(
        `/api/v1/trades/${tradeId}/notes/${noteId}`,
        payload
      );
      return res.data.data;
    },
    onSuccess: (_data, { tradeId }) => {
      void qc.invalidateQueries({ queryKey: ["notes", tradeId] });
    },
  });
}

export function useDeleteNote() {
  const qc = useQueryClient();
  return useMutation<void, Error, { tradeId: string; noteId: string }>({
    mutationFn: async ({ tradeId, noteId }) => {
      await apiClient.delete(
        `/api/v1/trades/${tradeId}/notes/${noteId}`
      );
    },
    onSuccess: (_data, { tradeId }) => {
      void qc.invalidateQueries({ queryKey: ["notes", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
