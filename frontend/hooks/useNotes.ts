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
 * React Query hooks for trade notes CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listNotesApiV1TradesTradeIdNotesGet,
  createNoteApiV1TradesTradeIdNotesPost,
  updateNoteApiV1TradesTradeIdNotesNoteIdPatch,
  deleteNoteApiV1TradesTradeIdNotesNoteIdDelete,
} from "@/lib/api/index";
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
      const { data, error } = await listNotesApiV1TradesTradeIdNotesGet({
        path: { trade_id: tradeId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return ((data as unknown as ResponseEnvelope<TradeNote[]>).data) ?? [];
    },
    staleTime: 30 * 1000,
    enabled: Boolean(tradeId),
  });
}

export function useAddNote() {
  const qc = useQueryClient();
  return useMutation<TradeNote, Error, { tradeId: string; payload: TradeNoteCreate }>({
    mutationFn: async ({ tradeId, payload }) => {
      const { data, error } = await createNoteApiV1TradesTradeIdNotesPost({
        path: { trade_id: tradeId },
        body: payload as import("@/lib/api/types.gen").TradeNoteCreate,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as ResponseEnvelope<TradeNote>).data;
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
      const { data, error } = await updateNoteApiV1TradesTradeIdNotesNoteIdPatch({
        path: { trade_id: tradeId, note_id: noteId },
        body: payload as import("@/lib/api/types.gen").TradeNoteUpdate,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as unknown as ResponseEnvelope<TradeNote>).data;
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
      const { error } = await deleteNoteApiV1TradesTradeIdNotesNoteIdDelete({
        path: { trade_id: tradeId, note_id: noteId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, { tradeId }) => {
      void qc.invalidateQueries({ queryKey: ["notes", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
