/**
 * React Query hooks for Schwab broker connection management.
 *
 * - useSchwabStatus: polls connection status (connected, last_sync_at)
 * - useSchwabSync: mutation to trigger a trade sync
 * - useDisconnectSchwab: mutation to remove the Schwab connection
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { BrokerStatusResponse, ResponseEnvelope, SchwabSyncResult } from "@/lib/types";

// ─── Query keys ───────────────────────────────────────────────────────────────

export const SCHWAB_STATUS_KEY = ["broker", "schwab", "status"] as const;

// ─── useSchwabStatus ──────────────────────────────────────────────────────────

/**
 * Fetches the current Schwab connection status for the authenticated user.
 */
export function useSchwabStatus() {
  return useQuery<BrokerStatusResponse, Error>({
    queryKey: SCHWAB_STATUS_KEY,
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<BrokerStatusResponse>>(
        "/api/v1/broker/schwab/status"
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}

// ─── useSchwabSync ────────────────────────────────────────────────────────────

/**
 * Triggers a Schwab trade sync. Invalidates status and trades queries on success.
 */
export function useSchwabSync() {
  const qc = useQueryClient();
  return useMutation<SchwabSyncResult, Error, void>({
    mutationFn: async () => {
      const res = await apiClient.post<ResponseEnvelope<SchwabSyncResult>>(
        "/api/v1/broker/schwab/sync"
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SCHWAB_STATUS_KEY });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}

// ─── useDisconnectSchwab ──────────────────────────────────────────────────────

/**
 * Removes the Schwab broker connection for the authenticated user.
 */
export function useDisconnectSchwab() {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await apiClient.delete("/api/v1/broker/schwab/disconnect");
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SCHWAB_STATUS_KEY });
    },
  });
}
