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
  Trade,
} from "@/lib/types";

/** Fetch all executions for a trade. */
export function useTradeExecutions(tradeId: string) {
  return useQuery<LogicalExecution[], Error>({
    queryKey: ["executions", tradeId],
    queryFn: async () => {
      const res = await apiClient.get<ResponseEnvelope<LogicalExecution[]>>(
        `/api/v1/trades/${tradeId}/executions`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
    enabled: Boolean(tradeId),
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
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
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
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}

/** Delete an execution. */
export function useDeleteExecution() {
  const qc = useQueryClient();
  return useMutation<void, Error, { executionId: string; tradeId: string }>({
    mutationFn: async ({ executionId }) => {
      await apiClient.delete(`/api/v1/executions/${executionId}`);
    },
    onSuccess: (_, { tradeId }) => {
      void qc.invalidateQueries({ queryKey: ["executions", tradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", tradeId] });
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
      void qc.invalidateQueries({ queryKey: ["executions", sourceTradeId] });
      void qc.invalidateQueries({ queryKey: ["executions", target_trade_id] });
      void qc.invalidateQueries({ queryKey: ["trade", sourceTradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", target_trade_id] });
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
      void qc.invalidateQueries({ queryKey: ["executions", sourceTradeId] });
      void qc.invalidateQueries({ queryKey: ["trade", sourceTradeId] });
      void qc.invalidateQueries({ queryKey: ["trades"] });
    },
  });
}
