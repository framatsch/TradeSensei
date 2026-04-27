/**
 * React Query hooks for the user's broker accounts.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
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
      const res = await apiClient.get<ResponseEnvelope<CursorPage<Account>>>(url);
      return res.data.data.items;
    },
    staleTime: 5 * 60 * 1000,
    enabled: portfolioId !== undefined || portfolioId === undefined, // always enabled, but nice for logic
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation<Account, Error, AccountCreate>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<Account>>(
        "/api/v1/accounts",
        payload
      );
      return res.data.data;
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
      const res = await apiClient.patch<ResponseEnvelope<Account>>(
        `/api/v1/accounts/${id}`,
        payload
      );
      return res.data.data;
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
      await apiClient.delete(`/api/v1/accounts/${id}`);
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
