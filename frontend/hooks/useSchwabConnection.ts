/**
 * React Query hooks for Schwab broker connection management.
 *
 * - useSchwabStatus: polls connection status (connected, last_sync_at)
 * - useSchwabSync: mutation to trigger a trade sync
 * - useDisconnectSchwab: mutation to remove the Schwab connection
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { BrokerStatusResponse, BrokerSyncResult } from "@/lib/types";

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
      const response = await client.get({ url: "/api/v1/broker/schwab/status" });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as BrokerStatusResponse;
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
  return useMutation<BrokerSyncResult, Error, void>({
    mutationFn: async () => {
      const response = await client.post({ url: "/api/v1/broker/schwab/sync" });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as BrokerSyncResult;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SCHWAB_STATUS_KEY });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
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
      await client.delete({ url: "/api/v1/broker/schwab/disconnect" });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SCHWAB_STATUS_KEY });
    },
  });
}
