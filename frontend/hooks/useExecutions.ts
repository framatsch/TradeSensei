/**
 * React Query hooks for LogicalExecution CRUD operations.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type {
  LogicalExecution,
  LogicalExecutionCreate,
  LogicalExecutionUpdate,
  ReassignExecutionRequest,
  ResponseEnvelope,
  SplitExecutionRequest,
  SplitExecutionResponse,
  Trade,
} from "@/lib/types";

/**
 * Fetch executions for a trade.
 *
 * @param tradeId - Trade UUID.
 * @param includeDeleted - When true, include soft-deleted executions (task 8.4).
 */
export function useTradeExecutions(tradeId: string, includeDeleted = false) {
  return useQuery<LogicalExecution[], Error>({
    queryKey: ["executions", tradeId, { includeDeleted }],
    queryFn: async () => {
      const url = `/api/v1/trades/${tradeId}/executions${includeDeleted ? "?include_deleted=true" : ""}`;
      const res = await apiClient.get<ResponseEnvelope<LogicalExecution[]>>(url);
      return res.data.data;
    },
    staleTime: 5 * 1000, // 5 seconds to ensure fresh data after updates
    enabled: Boolean(tradeId),
  });
}

/** Restore a soft-deleted execution (task 8.5). */
export function useRestoreExecution() {
  const qc = useQueryClient();
  return useMutation<LogicalExecution, Error, { executionId: string; tradeId: string }>({
    mutationFn: async ({ executionId }) => {
      const res = await apiClient.post<ResponseEnvelope<LogicalExecution>>(
        `/api/v1/executions/${executionId}/restore`
      );
      return res.data.data;
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
      const res = await apiClient.post<ResponseEnvelope<LogicalExecution>>(
        `/api/v1/trades/${tradeId}/executions`,
        payload
      );
      return res.data.data;
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
      const res = await apiClient.patch<ResponseEnvelope<LogicalExecution>>(
        `/api/v1/executions/${executionId}`,
        data
      );
      return res.data.data;
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
      const res = await apiClient.delete<ResponseEnvelope<LogicalExecution> | "">(
        `/api/v1/executions/${executionId}`
      );
      // 204 → empty body; 200 → envelope with soft-deleted execution
      if (res.status === 204 || !res.data) return null;
      return (res.data as ResponseEnvelope<LogicalExecution>).data;
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
      const res = await apiClient.post<ResponseEnvelope<LogicalExecution>>(
        `/api/v1/executions/${executionId}/reassign`,
        { target_trade_id }
      );
      return res.data.data;
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
      const res = await apiClient.post<ResponseEnvelope<Trade>>(
        `/api/v1/executions/${executionId}/detach`
      );
      return res.data.data;
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
      const res = await apiClient.post<ResponseEnvelope<SplitExecutionResponse>>(
        `/api/v1/executions/${executionId}/split`,
        data
      );
      return res.data.data;
    },
    onSuccess: (_, { tradeId }) => {
      // Invalidate all execution query variants (deleted included or not)
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.refetchQueries({ queryKey: ["trade", tradeId], type: "all" });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
