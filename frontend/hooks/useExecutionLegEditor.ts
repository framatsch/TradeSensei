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

"use client";

import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useUpdateExecution, useDeleteExecution, useRestoreExecution } from "@/hooks/useExecutions";
import { extractApiError } from "@/lib/apiErrors";
import type { Direction, LogicalExecution } from "@/lib/types";

const decimalString = z.string().trim().min(1, "A number is required.").refine(
  (value) => Number.isFinite(Number(value)),
  "Enter a valid number.",
);

const draftSchema = z.object({
  direction: z.enum(["LONG", "SHORT"]),
  executedAt: z.string().refine((value) => value !== "" && Number.isFinite(new Date(value).getTime()), "Enter a valid execution date and time."),
  quantity: decimalString.refine((value) => Number(value) > 0, "Quantity must be greater than 0."),
  price: decimalString.refine((value) => Number(value) >= 0, "Price must not be negative."),
  commission: decimalString,
  pnl: z.string().trim().refine((value) => value === "" || Number.isFinite(Number(value)), "Enter a valid P&L."),
});

type ExecutionLegDraft = z.infer<typeof draftSchema>;

function buildDraft(execution: LogicalExecution): ExecutionLegDraft {
  const date = execution.executed_at ? new Date(execution.executed_at) : null;
  return {
    direction: execution.direction,
    executedAt: date ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "",
    quantity: execution.raw_quantity,
    price: execution.raw_price,
    commission: execution.commission,
    pnl: execution.pnl ?? "",
  };
}

export function useExecutionLegEditor(execution: LogicalExecution, tradeId: string) {
  const { activePortfolioId } = useActivePortfolio();
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const { control, setValue, reset, handleSubmit } = useForm<ExecutionLegDraft>({
    resolver: zodResolver(draftSchema),
    defaultValues: buildDraft(execution),
  });
  const [editDirection, editExecutedAt, editQty, editPrice, editCommission, editPnl] = useWatch({
    control,
    name: ["direction", "executedAt", "quantity", "price", "commission", "pnl"],
  });

  const updateExecution = useUpdateExecution();
  const deleteExecution = useDeleteExecution();
  const restoreExecution = useRestoreExecution();

  useEffect(() => {
    if (!isEditing) reset(buildDraft(execution));
  }, [execution, isEditing, reset]);

  const isLong = execution.direction === "LONG";
  const isDeleted = execution.deleted === true;
  const canSplit = !isDeleted && (execution.origin === "imported" || execution.origin === "manual");
  const canLinkBroker = !isDeleted && execution.origin === "manual" && !execution.source_id;

  const handleSave = handleSubmit((values) => {
    if (!activePortfolioId) return;
    setErrorMsg(null);
    updateExecution.mutate(
      {
        executionId: execution.id,
        tradeId,
        portfolioId: activePortfolioId,
        data: {
          direction: values.direction,
          executed_at: new Date(values.executedAt).toISOString(),
          price: values.price,
          quantity: values.quantity,
          commission: values.commission,
          pnl: values.pnl === "" ? null : values.pnl,
        },
      },
      {
        onSuccess: () => setIsEditing(false),
        onError: (error) => setErrorMsg(extractApiError(error, "Failed to save execution.")),
      },
    );
  }, (errors) => {
    setErrorMsg(Object.values(errors).find((error) => error?.message)?.message ?? "Check the execution fields.");
  });

  function handleCancel() {
    reset(buildDraft(execution));
    setErrorMsg(null);
    setIsEditing(false);
  }

  function handleDelete() {
    setShowDeleteConfirm(true);
  }

  function confirmDelete() {
    if (!activePortfolioId) return;
    setErrorMsg(null);
    deleteExecution.mutate(
      { executionId: execution.id, tradeId, portfolioId: activePortfolioId },
      {
        onSettled: () => setShowDeleteConfirm(false),
        onError: (error) => setErrorMsg(extractApiError(error, "Failed to delete execution.")),
      },
    );
  }

  function handleRestore() {
    if (!activePortfolioId) return;
    setErrorMsg(null);
    restoreExecution.mutate(
      { executionId: execution.id, tradeId, portfolioId: activePortfolioId },
      { onError: (error) => setErrorMsg(extractApiError(error, "Failed to restore execution.")) },
    );
  }

  return {
    activePortfolioId,
    isEditing,
    setIsEditing,
    showDeleteConfirm,
    setShowDeleteConfirm,
    errorMsg,
    editPrice,
    setEditPrice: (value: string) => setValue("price", value),
    editQty,
    setEditQty: (value: string) => setValue("quantity", value),
    editCommission,
    setEditCommission: (value: string) => setValue("commission", value),
    editDirection,
    setEditDirection: (value: Direction) => setValue("direction", value),
    editExecutedAt,
    setEditExecutedAt: (value: string) => setValue("executedAt", value),
    editPnl,
    setEditPnl: (value: string) => setValue("pnl", value),
    updateExecution,
    deleteExecution,
    restoreExecution,
    isLong,
    isDeleted,
    canSplit,
    canLinkBroker,
    handleSave,
    handleCancel,
    handleDelete,
    confirmDelete,
    handleRestore,
  };
}
