/**
 * ExecutionRow — a single execution leg with inline edit and overflow menu.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { MoreHorizontal, ArrowUp, ArrowDown, Check, X } from "lucide-react";
import type { LogicalExecution } from "@/lib/types";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { useUpdateExecution, useDeleteExecution } from "@/hooks/useExecutions";

interface Props {
  execution: LogicalExecution;
  tradeId: string;
  onMoveToTrade?: (executionId: string) => void;
  onDetach?: (executionId: string) => void;
}

function fmt(value: string | null): string {
  if (!value) return "—";
  const num = parseFloat(value);
  return isNaN(num) ? "—" : `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
}

function fmtQty(value: string): string {
  const num = parseFloat(value);
  return isNaN(num) ? "—" : num.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

function fmtPnl(value: string | null) {
  if (!value) return <span className="text-muted-foreground">—</span>;
  const num = parseFloat(value);
  const color = num >= 0 ? "text-emerald-500" : "text-red-500";
  const prefix = num >= 0 ? "+" : "";
  return <span className={`font-medium ${color}`}>{prefix}${Math.abs(num).toFixed(2)}</span>;
}

function fmtDate(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function ExecutionRow({ execution, tradeId, onMoveToTrade, onDetach }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editPrice, setEditPrice] = useState(execution.price);
  const [editQty, setEditQty] = useState(execution.quantity);
  const [editCommission, setEditCommission] = useState(execution.commission);
  const menuRef = useRef<HTMLDivElement>(null);

  const updateExecution = useUpdateExecution();
  const deleteExecution = useDeleteExecution();

  const isLong = execution.direction === "LONG";

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSave() {
    updateExecution.mutate(
      {
        executionId: execution.id,
        tradeId,
        data: {
          price: editPrice,
          quantity: editQty,
          commission: editCommission,
        },
      },
      { onSuccess: () => setIsEditing(false) }
    );
  }

  function handleCancel() {
    setEditPrice(execution.price);
    setEditQty(execution.quantity);
    setEditCommission(execution.commission);
    setIsEditing(false);
  }

  function handleDelete() {
    setMenuOpen(false);
    setShowDeleteConfirm(true);
  }

  function confirmDelete() {
    deleteExecution.mutate(
      { executionId: execution.id, tradeId },
      { onSettled: () => setShowDeleteConfirm(false) }
    );
  }

  return (
    <>
      <tr className="border-b border-border hover:bg-muted/30 transition-colors">
        {/* Date */}
        <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
          {fmtDate(execution.executed_at)}
        </td>

        {/* Side badge */}
        <td className="px-3 py-2">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
              isLong
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800"
            }`}
          >
            {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
            {execution.direction}
          </span>
        </td>

        {/* Quantity */}
        <td className="px-3 py-2 text-sm text-right">
          {isEditing ? (
            <input
              type="number"
              value={editQty}
              onChange={(e) => setEditQty(e.target.value)}
              className="w-20 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right"
            />
          ) : (
            <span className="cursor-pointer" onClick={() => setIsEditing(true)}>{fmtQty(execution.quantity)}</span>
          )}
        </td>

        {/* Price */}
        <td className="px-3 py-2 text-sm text-right">
          {isEditing ? (
            <input
              type="number"
              value={editPrice}
              onChange={(e) => setEditPrice(e.target.value)}
              className="w-24 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right"
            />
          ) : (
            <span className="cursor-pointer" onClick={() => setIsEditing(true)}>{fmt(execution.price)}</span>
          )}
        </td>

        {/* Commission */}
        <td className="px-3 py-2 text-sm text-right text-muted-foreground">
          {isEditing ? (
            <input
              type="number"
              value={editCommission}
              onChange={(e) => setEditCommission(e.target.value)}
              className="w-20 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right"
            />
          ) : (
            <span className="cursor-pointer" onClick={() => setIsEditing(true)}>{fmt(execution.commission)}</span>
          )}
        </td>

        {/* P&L */}
        <td className="px-3 py-2 text-sm text-right">
          {fmtPnl(execution.pnl)}
        </td>

        {/* Status badge */}
        <td className="px-3 py-2">
          <ExecutionStatusBadge status={execution.status} />
        </td>

        {/* Actions */}
        <td className="px-3 py-2 text-right">
          {isEditing ? (
            <div className="inline-flex items-center gap-1">
              <button
                onClick={handleSave}
                disabled={updateExecution.isPending}
                className="p-1 rounded hover:bg-emerald-100 dark:hover:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400"
                title="Save"
              >
                <Check size={14} />
              </button>
              <button
                onClick={handleCancel}
                className="p-1 rounded hover:bg-muted text-muted-foreground"
                title="Cancel"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="p-1 rounded hover:bg-muted text-muted-foreground"
              >
                <MoreHorizontal size={14} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 z-50 mt-1 w-44 bg-popover border border-border rounded-lg shadow-lg py-1">
                  <button
                    onClick={() => { setIsEditing(true); setMenuOpen(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                  >
                    Edit
                  </button>
                  {onMoveToTrade && (
                    <button
                      onClick={() => { setMenuOpen(false); onMoveToTrade(execution.id); }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                    >
                      Move to...
                    </button>
                  )}
                  {onDetach && (
                    <button
                      onClick={() => { setMenuOpen(false); onDetach(execution.id); }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                    >
                      Detach as new Trade
                    </button>
                  )}
                  <button
                    onClick={handleDelete}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          )}
        </td>
      </tr>

      {showDeleteConfirm && (
        <tr>
          <td colSpan={8} className="px-3 py-3 bg-red-50/70 dark:bg-red-900/20 border-b border-border">
            <div className="flex items-center justify-between gap-3 text-xs">
              <span className="text-foreground">
                Delete this execution? This will re-aggregate the trade.
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="rounded px-2 py-1 text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmDelete}
                  disabled={deleteExecution.isPending}
                  className="rounded bg-red-600 px-2 py-1 text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deleteExecution.isPending ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
