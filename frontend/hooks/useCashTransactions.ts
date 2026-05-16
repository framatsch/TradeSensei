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
 * React Query hooks for cash transactions and account metrics.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type {
  AccountMetrics,
  CashTransaction,
  CashTransactionCreate,
  CashTransactionType,
  CashTransactionUpdate,
  OffsetPage,
} from "@/lib/types";

// ─── Options type ─────────────────────────────────────────────────────────────

export interface UseCashTransactionsOptions {
  account_id: string;
  offset?: number;
  limit?: number;
  type?: CashTransactionType | null;
  symbol?: string | null;
  from_date?: string | null;
  to_date?: string | null;
}

// ─── useCashTransactions ──────────────────────────────────────────────────────

export function useCashTransactions({
  account_id,
  offset = 0,
  limit = 50,
  type,
  symbol,
  from_date,
  to_date,
}: UseCashTransactionsOptions) {
  return useQuery<OffsetPage<CashTransaction>, Error>({
    queryKey: ["cash-transactions", account_id, offset, limit, type, symbol, from_date, to_date],
    queryFn: async () => {
      const query: Record<string, string | number> = { limit, offset };
      if (type) query.type = type;
      if (symbol) query.symbol = symbol;
      if (from_date) query.from_date = from_date;
      if (to_date) query.to_date = to_date;

      const response = await client.get({
        url: `/api/v1/accounts/${account_id}/cash-transactions`,
        query,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as OffsetPage<CashTransaction>;
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
      const response = await client.get({
        url: `/api/v1/accounts/${account_id}/metrics`,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as AccountMetrics;
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
      const response = await client.post({
        url: `/api/v1/accounts/${account_id}/cash-transactions`,
        body: data,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as CashTransaction;
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
      const response = await client.patch({
        url: `/api/v1/accounts/${account_id}/cash-transactions/${id}`,
        body: data,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as CashTransaction;
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
      await client.delete({
        url: `/api/v1/accounts/${account_id}/cash-transactions/${id}`,
      });
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["cash-transactions", variables.account_id] });
      void qc.invalidateQueries({ queryKey: ["account-metrics", variables.account_id] });
    },
  });
}
