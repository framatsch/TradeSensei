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

export function useAccounts() {
  return useQuery<Account[], Error>({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<CursorPage<Account>>>(
        "/api/v1/accounts"
      );
      return res.data.data.items;
    },
    staleTime: 5 * 60 * 1000,
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
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["accounts"] }),
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
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/accounts/${id}`);
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["accounts"] }),
  });
}
