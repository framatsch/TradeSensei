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
 * React Query hooks for LogicalExecution CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listTradeExecutionsApiV1PortfoliosPortfolioIdTradesTradeIdExecutionsGet as listTradeExecutions,
  createManualExecutionApiV1PortfoliosPortfolioIdTradesTradeIdExecutionsPost as createManualExecution,
  updateExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdPatch as updateExecution,
  deleteExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdDelete as deleteExecution,
  restoreExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdRestorePost as restoreExecution,
  reassignExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdReassignPost as reassignExecution,
  detachExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdDetachPost as detachExecution,
  splitExecutionApiV1PortfoliosPortfolioIdExecutionsExecutionIdSplitPost as splitExecution,
  linkBrokerTransactionApiV1PortfoliosPortfolioIdExecutionsExecutionIdLinkBrokerTransactionPost as linkBrokerTransaction,
  listBrokerTransactionsApiV1PortfoliosPortfolioIdBrokerTransactionsGet as listBrokerTransactions,
  type LogicalExecutionRead as GeneratedLogicalExecutionRead,
  type BrokerRawTransactionRead as GeneratedBrokerRawTransactionRead,
} from "@/lib/api/index";
import type {
  LogicalExecution,
  LogicalExecutionCreate,
  LogicalExecutionUpdate,
  ReassignExecutionRequest,
  SplitExecutionRequest,
  SplitExecutionResponse,
} from "@/lib/types";

export function mapGeneratedExecution(execution: GeneratedLogicalExecutionRead): LogicalExecution {
  return {
    id: execution.id,
    trade_id: execution.trade_id ?? null,
    user_id: execution.user_id,
    account_id: execution.account_id ?? null,
    symbol: execution.symbol,
    asset_class: execution.asset_class,
    conid: execution.conid ?? null,
    direction: execution.direction,
    quantity: execution.quantity,
    price: execution.price,
    raw_quantity: execution.raw_quantity ?? execution.quantity,
    raw_price: execution.raw_price ?? execution.price,
    // Backend always provides commission, defaulting to "0" defensively
    commission: execution.commission ?? "0",
    pnl: execution.pnl ?? null,
    pnl_eur: execution.pnl_eur ?? null,
    executed_at: execution.executed_at,
    origin: execution.origin,
    deleted: execution.deleted,
    user_modified: execution.user_modified,
    parent_id: execution.parent_id ?? null,
    source_id: execution.source_id ?? null,
    currency: execution.currency ?? null,
    multiplier: execution.multiplier,
    open_close: (execution.open_close as "O" | "C" | null | undefined) ?? null,
    strike: execution.strike ?? null,
    expiry: execution.expiry ?? null,
    option_type: (execution.option_type as "C" | "P" | null | undefined) ?? null,
    created_at: execution.created_at,
    updated_at: execution.updated_at,
  };
}

/**
 * Fetch executions for a trade.
 *
 * Query key: ["executions", portfolioId, tradeId, { includeDeleted }] (4-element)
 * Write hooks invalidate using the 3-element prefix ["executions", portfolioId, tradeId],
 * which covers both showDeleted=true and false variants via TanStack Query prefix matching.
 *
 * @param tradeId - Trade UUID.
 * @param includeDeleted - When true, include soft-deleted executions (task 8.4).
 */
export function useTradeExecutions(tradeId: string, portfolioId?: string | null, includeDeleted = false) {
  return useQuery<LogicalExecution[], Error>({
    queryKey: ["executions", portfolioId, tradeId, { includeDeleted }],
    queryFn: async () => {
      const { data, error } = await listTradeExecutions({
        path: { portfolio_id: portfolioId!, trade_id: tradeId },
        query: includeDeleted ? { include_deleted: true } : undefined,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return (data.data as GeneratedLogicalExecutionRead[]).map(mapGeneratedExecution);
    },
    staleTime: 5 * 1000, // 5 seconds to ensure fresh data after updates
    enabled: Boolean(tradeId) && Boolean(portfolioId),
  });
}

/** Restore a soft-deleted execution (task 8.5). */
export function useRestoreExecution() {
  const qc = useQueryClient();
  return useMutation<LogicalExecution, Error, { executionId: string; tradeId: string; portfolioId: string }>({
    mutationFn: async ({ executionId, portfolioId }) => {
      const { data, error } = await restoreExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return mapGeneratedExecution(data.data);
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Create a new manual execution for a trade. */
export function useCreateExecution() {
  const qc = useQueryClient();
  return useMutation<LogicalExecution, Error, { tradeId: string; portfolioId: string; data: LogicalExecutionCreate }>({
    mutationFn: async ({ tradeId, portfolioId, data: payload }) => {
      const { data, error } = await createManualExecution({
        path: { portfolio_id: portfolioId, trade_id: tradeId },
        body: payload,
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return mapGeneratedExecution(data.data);
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Update an existing execution. */
export function useUpdateExecution() {
  const qc = useQueryClient();
  return useMutation<
    LogicalExecution,
    Error,
    { executionId: string; tradeId: string; portfolioId: string; data: LogicalExecutionUpdate }
  >({
    mutationFn: async ({ executionId, portfolioId, data }) => {
      const { data: resData, error } = await updateExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
        body: data,
      });
      if (error || !resData) throw error ?? new Error("Request failed: no data returned");
      return mapGeneratedExecution(resData.data);
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/**
 * Delete an execution.
 *
 * Per the simplified-execution-model spec:
 *  - Imported/merged/split executions are soft-deleted (response: 200 + body).
 *  - Manual executions are hard-deleted (response: 204 no body).
 * In both cases, we refetch the execution list after the operation.
 *
 * Note: the backend also supports a reset-to-broker-state mode (restoring a
 * soft-deleted imported execution back to its original broker values). That
 * mode has no frontend entry point yet — it is backend/ops-only for now.
 */
export function useDeleteExecution() {
  const qc = useQueryClient();
  return useMutation<LogicalExecution | null, Error, { executionId: string; tradeId: string; portfolioId: string }>({
    mutationFn: async ({ executionId, portfolioId }) => {
      const { data, error, response } = await deleteExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
      });
      if (error) throw error;
      // 204 = hard-delete of manual execution (no body); @hey-api returns { data: {}, ... } for 204
      if (response?.status === 204) return null;
      if (!data?.data) return null;
      return mapGeneratedExecution(data.data);
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["broker-transactions"] });
    },
  });
}

/** Reassign an execution to a different trade. */
export function useReassignExecution() {
  const qc = useQueryClient();
  return useMutation<
    LogicalExecution,
    Error,
    { executionId: string; sourceTradeId: string; portfolioId: string } & ReassignExecutionRequest
  >({
    mutationFn: async ({ executionId, portfolioId, target_trade_id }) => {
      const { data, error } = await reassignExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
        body: { target_trade_id },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      // reassign returns ReassignExecutionResponse { execution, message } — hence .execution
      return mapGeneratedExecution(data.data.execution);
    },
    onSuccess: (_, { sourceTradeId, portfolioId, target_trade_id }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, sourceTradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, target_trade_id], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", sourceTradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", target_trade_id], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Detach an execution into a new trade. */
export function useDetachExecution() {
  const qc = useQueryClient();
  // The backend returns the newly created Trade (200 ResponseEnvelope[TradeRead]) to enable
  // post-detach navigation, but we intentionally discard it here — the product design is
  // "stay on current view and refresh". If post-detach navigation is added in future,
  // update the return type to Trade and surface data.data to the caller.
  return useMutation<void, Error, { executionId: string; sourceTradeId: string; portfolioId: string }>({
    mutationFn: async ({ executionId, portfolioId }) => {
      const { error } = await detachExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_, { sourceTradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, sourceTradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", sourceTradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Split an execution into two (task 8.9). */
export function useSplitExecution() {
  const qc = useQueryClient();
  return useMutation<
    SplitExecutionResponse,
    Error,
    { executionId: string; tradeId: string; portfolioId: string; data: SplitExecutionRequest }
  >({
    mutationFn: async ({ executionId, portfolioId, data }) => {
      const { data: resData, error } = await splitExecution({
        path: { portfolio_id: portfolioId, execution_id: executionId },
        body: data,
      });
      if (error || !resData) throw error ?? new Error("Request failed: no data returned");
      return {
        execution_a: mapGeneratedExecution(resData.data.execution_a),
        execution_b: mapGeneratedExecution(resData.data.execution_b),
        original: mapGeneratedExecution(resData.data.original),
      };
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/**
 * List broker raw transactions for the manual-link picker.
 *
 * Query key: ["broker-transactions", portfolioId, { accountId, symbol }].
 * Results are the candidate link targets for a manual execution; the
 * endpoint scopes to the authenticated user, so no cross-user leakage.
 */
export function useBrokerTransactions(
  portfolioId: string | null | undefined,
  accountId?: string | null,
  symbol?: string | null,
  enabled = true,
) {
  return useQuery<GeneratedBrokerRawTransactionRead[], Error>({
    queryKey: ["broker-transactions", portfolioId, { accountId, symbol }],
    queryFn: async () => {
      const { data, error } = await listBrokerTransactions({
        path: { portfolio_id: portfolioId! },
        query: {
          ...(accountId ? { account_id: accountId } : {}),
          ...(symbol ? { symbol } : {}),
        },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data.data as GeneratedBrokerRawTransactionRead[];
    },
    enabled: Boolean(portfolioId) && enabled,
    staleTime: 30 * 1000,
  });
}

/**
 * Link a manual execution to a broker raw transaction.
 *
 * On success the backend sets source_id on the execution and suppresses the
 * BRT, then re-aggregates — which may clear trade.has_conflict. We refetch
 * the execution list, the trade detail, and the trade list so the banner
 * and the pair highlight reflect the recomputed state.
 */
export function useLinkBrokerTransaction() {
  const qc = useQueryClient();
  return useMutation<
    LogicalExecution,
    Error,
    { executionId: string; tradeId: string; portfolioId: string; rawTransactionId: string }
  >({
    mutationFn: async ({ executionId, portfolioId, rawTransactionId }) => {
      const { data, error } = await linkBrokerTransaction({
        path: { portfolio_id: portfolioId, execution_id: executionId },
        body: { raw_transaction_id: rawTransactionId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return mapGeneratedExecution(data.data.execution);
    },
    onSuccess: (_, { tradeId, portfolioId }) => {
      void qc.refetchQueries({ queryKey: ["executions", portfolioId, tradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
      void qc.invalidateQueries({ queryKey: ["broker-transactions"] });
    },
  });
}
