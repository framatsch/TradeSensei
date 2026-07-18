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
 * React Query hooks for the user's broker accounts.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { clearAccountTradesApiV1PortfoliosPortfolioIdAccountsAccountIdTradesDelete } from "@/lib/api/sdk.gen";
import type { ClearTradesResult } from "@/lib/api/types.gen";
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
    enabled: !!portfolioId,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Account, Error, AccountCreate>({
    mutationFn: async (payload) => {
      const url = portfolioId
        ? `/api/v1/portfolios/${portfolioId}/accounts`
        : "/api/v1/accounts";
      const { data, error } = await client.post<ResponseEnvelope<Account>, unknown, false>({
        url,
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
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<Account, Error, AccountUpdate>({
    mutationFn: async (payload) => {
      const url = portfolioId
        ? `/api/v1/portfolios/${portfolioId}/accounts/${id}`
        : `/api/v1/accounts/${id}`;
      const { data, error } = await client.patch<ResponseEnvelope<Account>, unknown, false>({
        url,
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

export function useClearAccountTrades() {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<ClearTradesResult, Error, string>({
    mutationFn: async (accountId) => {
      const { data, error } =
        await clearAccountTradesApiV1PortfoliosPortfolioIdAccountsAccountIdTradesDelete({
          path: { portfolio_id: portfolioId!, account_id: accountId },
          query: { acknowledged: true },
        });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data as ResponseEnvelope<ClearTradesResult>).data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["metrics"] });
      void qc.invalidateQueries({ queryKey: ["tax"] });
      void qc.invalidateQueries({ queryKey: ["stats"] });
      void qc.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  const portfolioId = usePortfolioStore((state) => state.activePortfolioId);
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const url = portfolioId
        ? `/api/v1/portfolios/${portfolioId}/accounts/${id}`
        : `/api/v1/accounts/${id}`;
      const { error } = await client.delete<unknown, unknown, false>({
        url,
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
