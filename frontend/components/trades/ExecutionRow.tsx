/**
 * ExecutionRow — a single execution leg with inline edit and overflow menu.
 *
 * Implements task 8.4 / 8.5:
 * - Deleted rows rendered at 50% opacity with a [Restore] button.
 * - Non-deleted rows get the normal edit + menu actions.
 * - "Split" option in the overflow menu for non-deleted imported/manual executions.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { MoreHorizontal, ArrowUp, ArrowDown, Check, X, Undo2 } from "lucide-react";
import type { LogicalExecution } from "@/lib/types";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { useUpdateExecution, useDeleteExecution, useRestoreExecution } from "@/hooks/useExecutions";

interface Props {
  execution: LogicalExecution;
  tradeId: string;
  onMoveToTrade?: (executionId: string) => void;
  onDetach?: (executionId: string) => void;
  onSplit?: (execution: LogicalExecution) => void;
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

export function ExecutionRow({ execution, tradeId, onMoveToTrade, onDetach, onSplit }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editPrice, setEditPrice] = useState(execution.price);
  const [editQty, setEditQty] = useState(execution.quantity);
  const [editCommission, setEditCommission] = useState(execution.commission);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);

  const updateExecution = useUpdateExecution();
  const deleteExecution = useDeleteExecution();
  const restoreExecution = useRestoreExecution();

  const isLong = execution.direction === "LONG";
  const isDeleted = execution.deleted === true;

  // Determine if this execution can be split (non-deleted, imported or manual origin)
  const canSplit = !isDeleted && (execution.origin === "imported" || execution.origin === "manual");

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node) &&
          buttonRef.current && !buttonRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (menuOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + window.scrollY + 4,
        left: rect.right + window.scrollX - 176, // 176px = w-44
      });
    }
  }, [menuOpen]);

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

  function handleRestore() {
    restoreExecution.mutate({ executionId: execution.id, tradeId });
  }

  // Deleted rows: 50% opacity, Restore button only
  if (isDeleted) {
    return (
      <tr className="border-b border-border opacity-50">
        {/* Date */}
        <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
          {fmtDate(execution.executed_at)}
        </td>

        {/* Side badge */}
        <td className="px-3 py-2">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
              isLong
                ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                : "bg-red-100 text-red-700 border border-red-200"
            }`}
          >
            {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
            {execution.direction}
          </span>
        </td>

        <td className="px-3 py-2 text-sm text-right">{fmtQty(execution.quantity)}</td>
        <td className="px-3 py-2 text-sm text-right">{fmt(execution.price)}</td>
        <td className="px-3 py-2 text-sm text-right text-muted-foreground">{fmt(execution.commission)}</td>
        <td className="px-3 py-2 text-sm text-right">{fmtPnl(execution.pnl)}</td>

        {/* Status badge — shows "Deleted" */}
        <td className="px-3 py-2">
          <ExecutionStatusBadge origin={execution.origin} deleted={true} user_modified={execution.user_modified} />
        </td>

        {/* Restore action */}
        <td className="px-3 py-2 text-right">
          <button
            onClick={handleRestore}
            disabled={restoreExecution.isPending}
            title="Restore this execution"
            className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-muted text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors disabled:opacity-50"
          >
            <Undo2 size={12} />
            Restore
          </button>
        </td>
      </tr>
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
                ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                : "bg-red-100 text-red-700 border border-red-200"
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
          <ExecutionStatusBadge
            origin={execution.origin}
            deleted={execution.deleted}
            user_modified={execution.user_modified}
          />
        </td>

         {/* Actions */}
         <td className="px-3 py-2 text-right">
           {isEditing ? (
             <div className="inline-flex items-center gap-1">
               <button
                 onClick={handleSave}
                 disabled={updateExecution.isPending}
                 className="p-1 rounded hover:bg-emerald-100 text-emerald-600"
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
             <>
               <button
                 ref={buttonRef}
                 onClick={() => setMenuOpen(!menuOpen)}
                 className="p-1 rounded hover:bg-muted text-muted-foreground"
               >
                 <MoreHorizontal size={14} />
               </button>
               {menuOpen && menuPosition && createPortal(
                 <div
                   ref={menuRef}
                   className="fixed z-50 w-44 bg-popover border border-border rounded-lg shadow-lg py-1"
                   style={{
                     top: `${menuPosition.top}px`,
                     left: `${menuPosition.left}px`,
                   }}
                 >
                   <button
                     onClick={() => { setIsEditing(true); setMenuOpen(false); }}
                     className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                   >
                     Edit
                   </button>
                   {canSplit && onSplit && (
                     <button
                       onClick={() => { setMenuOpen(false); onSplit(execution); }}
                       className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                     >
                       Split
                     </button>
                   )}
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
                     className="w-full text-left px-3 py-1.5 text-xs hover:bg-red-50 text-red-600"
                   >
                     Delete
                   </button>
                 </div>,
                 document.body
               )}
             </>
           )}
         </td>
      </tr>

      {showDeleteConfirm && (
        <tr>
          <td colSpan={8} className="px-3 py-3 bg-muted/50 border-b border-border">
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
