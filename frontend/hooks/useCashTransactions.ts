/**
 * React Query hooks for cash transactions and account metrics.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  AccountMetrics,
  CashTransaction,
  CashTransactionCreate,
  CashTransactionType,
  CashTransactionUpdate,
  CursorPage,
} from "@/lib/types";

// ─── Options type ─────────────────────────────────────────────────────────────

export interface UseCashTransactionsOptions {
  account_id: string;
  cursor?: string | null;
  limit?: number;
  type?: CashTransactionType | null;
  symbol?: string | null;
  from_date?: string | null;
  to_date?: string | null;
}

// ─── useCashTransactions ──────────────────────────────────────────────────────

export function useCashTransactions({
  account_id,
  cursor,
  limit = 20,
  type,
  symbol,
  from_date,
  to_date,
}: UseCashTransactionsOptions) {
  return useQuery<CursorPage<CashTransaction>, Error>({
    queryKey: ["cash-transactions", account_id, cursor, limit, type, symbol, from_date, to_date],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      if (cursor) params.set("cursor", cursor);
      if (type) params.set("type", type);
      if (symbol) params.set("symbol", symbol);
      if (from_date) params.set("from_date", from_date);
      if (to_date) params.set("to_date", to_date);

      // Direct response — no ResponseEnvelope wrapper
      const res = await apiClient.get<CursorPage<CashTransaction>>(
        `/api/v1/accounts/${account_id}/cash-transactions?${params.toString()}`
      );
      return res.data;
    },
    enabled: Boolean(account_id),
    staleTime: 30 * 1000,
  });
}

// ─── useAccountMetrics ────────────────────────────────────────────────────────

export function useAccountMetrics(account_id: string) {
  return useQuery<AccountMetrics, Error>({
    queryKey: ["account-metrics", account_id],
    queryFn: async () => {
      // Direct response — no ResponseEnvelope wrapper
      const res = await apiClient.get<AccountMetrics>(
        `/api/v1/accounts/${account_id}/metrics`
      );
      return res.data;
    },
    enabled: Boolean(account_id),
    staleTime: 30 * 1000,
  });
}

// ─── Mutation payload types ───────────────────────────────────────────────────

interface UpdateCashTransactionPayload {
  id: string;
  account_id: string;
  data: CashTransactionUpdate;
}

interface DeleteCashTransactionPayload {
  id: string;
  account_id: string;
}

// ─── useCreateCashTransaction ─────────────────────────────────────────────────

export function useCreateCashTransaction() {
  const qc = useQueryClient();
  return useMutation<CashTransaction, Error, { account_id: string; data: CashTransactionCreate }>({
    mutationFn: async ({ account_id, data }) => {
      const res = await apiClient.post<CashTransaction>(
        `/api/v1/accounts/${account_id}/cash-transactions`,
        data
      );
      return res.data;
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["cash-transactions", variables.account_id] });
      void qc.invalidateQueries({ queryKey: ["account-metrics", variables.account_id] });
    },
  });
}

// ─── useUpdateCashTransaction ─────────────────────────────────────────────────

export function useUpdateCashTransaction() {
  const qc = useQueryClient();
  return useMutation<CashTransaction, Error, UpdateCashTransactionPayload>({
    mutationFn: async ({ id, account_id, data }) => {
      const res = await apiClient.patch<CashTransaction>(
        `/api/v1/accounts/${account_id}/cash-transactions/${id}`,
        data
      );
      return res.data;
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["cash-transactions", variables.account_id] });
      void qc.invalidateQueries({ queryKey: ["account-metrics", variables.account_id] });
    },
  });
}

// ─── useDeleteCashTransaction ─────────────────────────────────────────────────

export function useDeleteCashTransaction() {
  const qc = useQueryClient();
  return useMutation<void, Error, DeleteCashTransactionPayload>({
    mutationFn: async ({ id, account_id }) => {
      await apiClient.delete(
        `/api/v1/accounts/${account_id}/cash-transactions/${id}`
      );
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["cash-transactions", variables.account_id] });
      void qc.invalidateQueries({ queryKey: ["account-metrics", variables.account_id] });
    },
  });
}
