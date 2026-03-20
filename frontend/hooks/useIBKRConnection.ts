/**
 * React Query hooks for IBKR Flex Query connection management.
 *
 * - useIBKRStatus: polls IBKR connection status
 * - useConnectIBKR: mutation to save Flex credentials
 * - useDisconnectIBKR: mutation to remove stored IBKR credentials
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { BrokerStatusResponse, ResponseEnvelope } from "@/lib/types";

// Inline payload type — IBKRConnectRequest was removed from types.ts as part of
// the account-centric broker sync refactor. These global-connect endpoints are
// deprecated but the hook is kept to avoid breaking existing references.
interface IBKRConnectPayload {
  flex_query_id: string;
  flex_token: string;
}

// ─── Query key ────────────────────────────────────────────────────────────────

export const IBKR_STATUS_KEY = ["broker", "ibkr", "status"] as const;

// ─── useIBKRStatus ────────────────────────────────────────────────────────────

/**
 * Fetches the current IBKR Flex connection status for the authenticated user.
 */
export function useIBKRStatus() {
  return useQuery<BrokerStatusResponse, Error>({
    queryKey: IBKR_STATUS_KEY,
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<BrokerStatusResponse>>(
        "/api/v1/broker/ibkr/status"
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}

// ─── useConnectIBKR ───────────────────────────────────────────────────────────

/**
 * Saves IBKR Flex credentials to the backend.
 * Invalidates the IBKR status query on success.
 */
export function useConnectIBKR() {
  const qc = useQueryClient();
  return useMutation<BrokerStatusResponse, Error, IBKRConnectPayload>({
    mutationFn: async (payload: IBKRConnectPayload) => {
      const res = await apiClient.post<ResponseEnvelope<BrokerStatusResponse>>(
        "/api/v1/broker/ibkr/connect",
        payload
      );
      return res.data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IBKR_STATUS_KEY });
    },
  });
}

// ─── useDisconnectIBKR ────────────────────────────────────────────────────────

/**
 * Removes the IBKR Flex connection for the authenticated user.
 */
export function useDisconnectIBKR() {
  const qc = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await apiClient.delete("/api/v1/broker/ibkr/disconnect");
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IBKR_STATUS_KEY });
    },
  });
}
