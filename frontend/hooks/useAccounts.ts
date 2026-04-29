/**
 * React Query hooks for the user's broker accounts.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type {
  Account,
  AccountCreate,
  AccountUpdate,
  CursorPage,
  ResponseEnvelope,
} from "@/lib/types";

export function useAccounts(portfolioId?: string) {
  return useQuery<Account[], Error>({
    queryKey: ["accounts", portfolioId],
    queryFn: async () => {
      const url = portfolioId
        ? `/api/v1/portfolios/${portfolioId}/accounts`
        : "/api/v1/accounts";
      const { data, error } = await client.get<ResponseEnvelope<CursorPage<Account>>, unknown, false>({
        url,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data.items;
    },
    staleTime: 5 * 60 * 1000,
    enabled: portfolioId !== undefined || portfolioId === undefined, // always enabled
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation<Account, Error, AccountCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.post<ResponseEnvelope<Account>, unknown, false>({
        url: "/api/v1/accounts",
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["accounts"] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}

export function useUpdateAccount(id: string) {
  const qc = useQueryClient();
  return useMutation<Account, Error, AccountUpdate>({
    mutationFn: async (payload) => {
      const { data, error } = await client.patch<ResponseEnvelope<Account>, unknown, false>({
        url: "/api/v1/accounts/{account_id}",
        path: { account_id: id },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["accounts"] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const { error } = await client.delete<unknown, unknown, false>({
        url: "/api/v1/accounts/{account_id}",
        path: { account_id: id },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["accounts"] });
      await qc.invalidateQueries({ queryKey: ["trades"] });
      await qc.invalidateQueries({ queryKey: ["stats"] });
      await qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
    },
  });
}
