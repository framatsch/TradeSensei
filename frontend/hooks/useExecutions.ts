/**
 * React Query hooks for LogicalExecution CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import {
  listTradeExecutionsApiV1PortfoliosPortfolioIdTradesTradeIdExecutionsGet,
  type LogicalExecutionRead as GeneratedLogicalExecutionRead,
} from "@/lib/api/index";
import type {
  LogicalExecution,
  LogicalExecutionCreate,
  LogicalExecutionUpdate,
  ReassignExecutionRequest,
  SplitExecutionRequest,
  SplitExecutionResponse,
  Trade,
} from "@/lib/types";

function mapGeneratedExecution(execution: GeneratedLogicalExecutionRead): LogicalExecution {
  return {
    id: execution.id,
    trade_id: execution.trade_id ?? null,
    user_id: execution.user_id,
    account_id: execution.account_id ?? null,
    symbol: execution.symbol,
    asset_class: execution.asset_class,
    direction: execution.direction,
    quantity: execution.quantity,
    price: execution.price,
    commission: execution.commission ?? "0",
    pnl: execution.pnl ?? null,
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
 * @param tradeId - Trade UUID.
 * @param includeDeleted - When true, include soft-deleted executions (task 8.4).
 */
export function useTradeExecutions(tradeId: string, portfolioId?: string | null, includeDeleted = false) {
  return useQuery<LogicalExecution[], Error>({
    queryKey: ["executions", portfolioId, tradeId, { includeDeleted }],
    queryFn: async () => {
      const { data, error } = await listTradeExecutionsApiV1PortfoliosPortfolioIdTradesTradeIdExecutionsGet({
        path: { portfolio_id: portfolioId!, trade_id: tradeId },
        query: includeDeleted ? { include_deleted: true } : undefined,
      });
      if (error || !data) throw error;
      return (data.data as GeneratedLogicalExecutionRead[]).map(mapGeneratedExecution);
    },
    staleTime: 5 * 1000, // 5 seconds to ensure fresh data after updates
    enabled: Boolean(tradeId) && Boolean(portfolioId),
  });
}

/** Restore a soft-deleted execution (task 8.5). */
export function useRestoreExecution() {
  const qc = useQueryClient();
  return useMutation<LogicalExecution, Error, { executionId: string; tradeId: string }>({
    mutationFn: async ({ executionId }) => {
      const response = await client.post({
        url: `/api/v1/executions/${executionId}/restore`,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as LogicalExecution;
    },
    onSuccess: (_, { tradeId }) => {
      // Refetch both the regular and deleted-included execution lists
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Create a new manual execution for a trade. */
export function useCreateExecution(tradeId: string) {
  const qc = useQueryClient();
  return useMutation<LogicalExecution, Error, LogicalExecutionCreate>({
    mutationFn: async (payload) => {
      const response = await client.post({
        url: `/api/v1/trades/${tradeId}/executions`,
        body: payload,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as LogicalExecution;
    },
    onSuccess: () => {
      // Force immediate refetch of executions
      void qc.refetchQueries({ queryKey: ["executions", tradeId], type: "all" });
      // Force immediate refetch of trade (P&L, etc will be re-calculated server-side)
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
    { executionId: string; tradeId: string; data: LogicalExecutionUpdate }
  >({
    mutationFn: async ({ executionId, data }) => {
      const response = await client.patch({
        url: `/api/v1/executions/${executionId}`,
        body: data,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as LogicalExecution;
    },
    onSuccess: (_, { tradeId }) => {
      // Force immediate refetch of executions (pnl field will be updated)
      void qc.refetchQueries({ queryKey: ["executions", tradeId], type: "all" });
      // Force immediate refetch of trade (P&L, etc will be re-calculated server-side)
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
  return useMutation<LogicalExecution | null, Error, { executionId: string; tradeId: string }>({
    mutationFn: async ({ executionId }) => {
      const response = await client.delete({
        url: `/api/v1/executions/${executionId}`,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      // 204 → empty body; 200 → envelope with soft-deleted execution
      if (!envelope.data) return null;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return ((envelope.data as any).data ?? envelope.data) as LogicalExecution;
    },
    onSuccess: (_, { tradeId }) => {
      // Invalidate all execution query variants (include_deleted true/false)
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
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
    { executionId: string; sourceTradeId: string } & ReassignExecutionRequest
  >({
    mutationFn: async ({ executionId, target_trade_id }) => {
      const response = await client.post({
        url: `/api/v1/executions/${executionId}/reassign`,
        body: { target_trade_id },
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as LogicalExecution;
    },
    onSuccess: (_, { sourceTradeId, target_trade_id }) => {
      // Force immediate refetch of both execution lists
      void qc.refetchQueries({ queryKey: ["executions", sourceTradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["executions", target_trade_id], type: "all" });
      // Force immediate refetch of both trades (P&L will be re-calculated server-side)
      void qc.refetchQueries({ queryKey: ["trade", sourceTradeId], type: "all" });
      void qc.refetchQueries({ queryKey: ["trade", target_trade_id], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Detach an execution into a new trade. */
export function useDetachExecution() {
  const qc = useQueryClient();
  return useMutation<
    Trade,
    Error,
    { executionId: string; sourceTradeId: string }
  >({
    mutationFn: async ({ executionId }) => {
      const response = await client.post({
        url: `/api/v1/executions/${executionId}/detach`,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as Trade;
    },
      onSuccess: (_, { sourceTradeId }) => {
        // Force immediate refetch of executions
        void qc.refetchQueries({ queryKey: ["executions", sourceTradeId], type: "all" });
        // Force immediate refetch of trade (P&L will be re-calculated server-side)
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
    { executionId: string; tradeId: string; data: SplitExecutionRequest }
  >({
    mutationFn: async ({ executionId, data }) => {
      const response = await client.post({
        url: `/api/v1/executions/${executionId}/split`,
        body: data,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      return (envelope.data?.data ?? envelope.data) as SplitExecutionResponse;
    },
    onSuccess: (_, { tradeId }) => {
      // Invalidate all execution query variants (deleted included or not)
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
