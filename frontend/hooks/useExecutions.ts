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
  type LogicalExecutionRead as GeneratedLogicalExecutionRead,
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
    // Backend always provides commission, defaulting to "0" defensively
    commission: execution.commission ?? "0",
    pnl: execution.pnl ?? null,
    pnl_eur: execution.pnl_eur ?? null,
    executed_at: execution.executed_at,
    origin: execution.origin,
    deleted: execution.deleted,
    user_modified: execution.user_modified,
    parent_id: execution.parent_id ?? null,
    currency: execution.currency ?? null,
    multiplier: execution.multiplier,
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
