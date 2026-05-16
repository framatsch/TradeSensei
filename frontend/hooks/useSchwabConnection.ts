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
