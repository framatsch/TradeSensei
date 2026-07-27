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
import type { LogicalExecution, Trade } from "@/lib/types";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { useUpdateExecution, useDeleteExecution, useRestoreExecution } from "@/hooks/useExecutions";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { extractApiError } from "@/lib/apiErrors";

interface Props {
  execution: LogicalExecution;
  trade: Trade;
  tradeId: string;
  onMoveToTrade?: (executionId: string) => void;
  onDetach?: (executionId: string) => void;
  onSplit?: (execution: LogicalExecution) => void;
  onLinkBroker?: (execution: LogicalExecution) => void;
  hasOptionLeg?: boolean;
  colSpan?: number;
  isConflict?: boolean;
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
  const color = num >= 0 ? "text-success" : "text-danger";
  const prefix = num >= 0 ? "+" : "";
  return <span className={`font-medium font-mono ${color}`}>{prefix}${Math.abs(num).toFixed(2)}</span>;
}

function fmtDate(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function fmtDateOnly(value: string): string {
  // Assume "YYYY-MM-DD" string; add time to avoid timezone shift on parsing
  return new Date(value + "T12:00:00Z").toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    timeZone: "UTC",
  });
}

function fmtOpenClose(value: "O" | "C" | null | undefined): string {
  if (value === "O") return "Open";
  if (value === "C") return "Close";
  return "—";
}

export function ExecutionRow({ execution, trade, tradeId, onMoveToTrade, onDetach, onSplit, onLinkBroker, hasOptionLeg, colSpan }: Props) {
  const { activePortfolioId } = useActivePortfolio();
  const [isEditing, setIsEditing] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [editPrice, setEditPrice] = useState(execution.raw_price);
  const [editQty, setEditQty] = useState(execution.raw_quantity);
  const [editCommission, setEditCommission] = useState(execution.commission);
  const [editDirection, setEditDirection] = useState(execution.direction);
  const [editExecutedAt, setEditExecutedAt] = useState(() => {
    // format to datetime-local: YYYY-MM-DDTHH:mm
    if (!execution.executed_at) return "";
    const d = new Date(execution.executed_at);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  const [editPnl, setEditPnl] = useState(execution.pnl ?? "");
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
  // Only unlinked manual legs can be linked to a broker transaction
  const canLinkBroker = !isDeleted && execution.origin === "manual" && !execution.source_id;

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
    if (!activePortfolioId) return;
    setErrorMsg(null);
    updateExecution.mutate(
      {
        executionId: execution.id,
        tradeId,
        portfolioId: activePortfolioId,
        data: {
          direction: editDirection,
          executed_at: new Date(editExecutedAt).toISOString(),
          price: editPrice,
          quantity: editQty,
          commission: editCommission,
          pnl: editPnl === "" ? null : editPnl,
        },
      },
      {
        onSuccess: () => setIsEditing(false),
        onError: (err) => setErrorMsg(extractApiError(err, "Failed to save execution.")),
      }
    );
  }

  function handleCancel() {
    setEditDirection(execution.direction);
    if (execution.executed_at) {
      const d = new Date(execution.executed_at);
      setEditExecutedAt(new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16));
    } else {
      setEditExecutedAt("");
    }
    setEditPrice(execution.raw_price);
    setEditQty(execution.raw_quantity);
    setEditCommission(execution.commission);
    setEditPnl(execution.pnl ?? "");
    setErrorMsg(null);
    setIsEditing(false);
  }

  function handleDelete() {
    setMenuOpen(false);
    setShowDeleteConfirm(true);
  }

  function confirmDelete() {
    if (!activePortfolioId) return;
    setErrorMsg(null);
    deleteExecution.mutate(
      { executionId: execution.id, tradeId, portfolioId: activePortfolioId },
      {
        onSettled: () => setShowDeleteConfirm(false),
        onError: (err) => setErrorMsg(extractApiError(err, "Failed to delete execution.")),
      }
    );
  }

  function handleRestore() {
    if (!activePortfolioId) return;
    restoreExecution.mutate({ executionId: execution.id, tradeId, portfolioId: activePortfolioId });
  }

  // Direction badge classes using semantic tokens
  const longBadgeCls = "bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-success border border-[color-mix(in_srgb,var(--success)_30%,transparent)]";
  const shortBadgeCls = "bg-[color-mix(in_srgb,var(--danger)_15%,transparent)] text-danger border border-[color-mix(in_srgb,var(--danger)_30%,transparent)]";

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
              isLong ? longBadgeCls : shortBadgeCls
            }`}
          >
            {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
            {execution.direction}
          </span>
        </td>

        {trade.is_combo && (
          <>
            <td className="px-3 py-2 text-sm text-muted-foreground">{fmtOpenClose(execution.open_close)}</td>
            <td className="px-3 py-2 text-sm text-foreground">{execution.symbol}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground">{execution.asset_class}</td>
          </>
        )}
        {hasOptionLeg && (
          <>
            <td className="px-3 py-2 text-sm text-right font-mono">{execution.strike ? fmt(execution.strike) : "—"}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground">{execution.option_type === "C" ? "Call" : execution.option_type === "P" ? "Put" : "—"}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground whitespace-nowrap">{execution.expiry ? fmtDateOnly(execution.expiry) : "—"}</td>
          </>
        )}

        <td className="px-3 py-2 text-sm text-right font-mono">{fmtQty(execution.quantity)}</td>
        <td className="px-3 py-2 text-sm text-right text-muted-foreground font-mono">
          {execution.multiplier === 1 ? "—" : execution.multiplier}
        </td>
        <td className="px-3 py-2 text-sm text-right font-mono">
          {fmt(execution.price)}
          {execution.multiplier > 1 && (
            <div className="text-[10px] text-muted-foreground">
              Notional: {fmt((parseFloat(execution.quantity) * parseFloat(execution.price) * execution.multiplier).toString())}
            </div>
          )}
        </td>
        <td className="px-3 py-2 text-sm text-right text-muted-foreground font-mono">{fmt(execution.commission)}</td>
        <td className="px-3 py-2 text-sm text-right">{fmtPnl(execution.pnl)}</td>

        {/* Lineage */}
        <td className="px-3 py-2 text-xs text-muted-foreground">
          {execution.parent_id ? (
            <span
              className="inline-flex items-center rounded border border-border bg-muted px-2 py-0.5 font-mono"
              title={`Parent execution: ${execution.parent_id}`}
            >
              {`↳ ${execution.parent_id.slice(0, 8)}`}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </td>

        {/* Status badge — shows "Deleted" */}
        <td className="px-3 py-2">
          <ExecutionStatusBadge
            origin={execution.origin}
            deleted={true}
            user_modified={execution.user_modified}
            parent_id={execution.parent_id}
          />
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
      <tr className={`border-b border-border transition-colors ${
        isConflict ? "bg-amber-500/10 border-l-[3px] border-l-amber-500 hover:bg-amber-500/20" : "hover:bg-[color-mix(in_srgb,var(--muted)_30%,transparent)]"
      }`}>
        {/* Date */}
        <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
          {isEditing ? (
            <input
              type="datetime-local"
              value={editExecutedAt}
              onChange={(e) => setEditExecutedAt(e.target.value)}
              aria-label="Executed at date and time"
              className="w-36 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground"
            />
          ) : (
            <span className="cursor-pointer" onClick={() => setIsEditing(true)}>{fmtDate(execution.executed_at)}</span>
          )}
        </td>

        {/* Side badge */}
        <td className="px-3 py-2">
          {isEditing ? (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => setEditDirection("LONG")}
                aria-label="Set direction to LONG"
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  editDirection === "LONG" ? longBadgeCls : "bg-muted text-muted-foreground border border-border"
                }`}
              >
                LONG
              </button>
              <button
                type="button"
                onClick={() => setEditDirection("SHORT")}
                aria-label="Set direction to SHORT"
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  editDirection === "SHORT" ? shortBadgeCls : "bg-muted text-muted-foreground border border-border"
                }`}
              >
                SHORT
              </button>
            </div>
          ) : (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider cursor-pointer ${
                isLong ? longBadgeCls : shortBadgeCls
              }`}
              onClick={() => setIsEditing(true)}
            >
              {isLong ? <ArrowUp size={10} strokeWidth={3} /> : <ArrowDown size={10} strokeWidth={3} />}
              {execution.direction}
            </span>
          )}
        </td>

        {trade.is_combo && (
          <>
            <td className="px-3 py-2 text-sm text-muted-foreground">{fmtOpenClose(execution.open_close)}</td>
            <td className="px-3 py-2 text-sm text-foreground">{execution.symbol}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground">{execution.asset_class}</td>
          </>
        )}
        {hasOptionLeg && (
          <>
            <td className="px-3 py-2 text-sm text-right font-mono">{execution.strike ? fmt(execution.strike) : "—"}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground">{execution.option_type === "C" ? "Call" : execution.option_type === "P" ? "Put" : "—"}</td>
            <td className="px-3 py-2 text-sm text-muted-foreground whitespace-nowrap">{execution.expiry ? fmtDateOnly(execution.expiry) : "—"}</td>
          </>
        )}

        {/* Quantity */}
        <td className="px-3 py-2 text-sm text-right">
          {isEditing ? (
            <input
              type="number"
              value={editQty}
              onChange={(e) => setEditQty(e.target.value)}
              aria-label="Quantity"
              className="w-20 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right font-mono"
            />
          ) : (
            <div className="inline-flex items-center justify-end gap-1.5">
              <span className="cursor-pointer font-mono" onClick={() => setIsEditing(true)}>{fmtQty(execution.quantity)}</span>
              {execution.origin === "split" && execution.parent_id && (
                <span
                  className="inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground"
                  title={`Proportionally allocated quantity from parent execution ${execution.parent_id}`}
                >
                  Allocated
                </span>
              )}
            </div>
          )}
        </td>

        {/* Multiplier */}
        <td className="px-3 py-2 text-sm text-right text-muted-foreground font-mono">
          {execution.multiplier === 1 ? "—" : execution.multiplier}
        </td>

        {/* Price */}
        <td className="px-3 py-2 text-sm text-right">
          {isEditing ? (
            <input
              type="number"
              value={editPrice}
              onChange={(e) => setEditPrice(e.target.value)}
              aria-label="Price"
              className="w-24 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right font-mono"
            />
          ) : (
            <>
              <div className="cursor-pointer font-mono" onClick={() => setIsEditing(true)}>{fmt(execution.price)}</div>
              {execution.multiplier > 1 && (
                <div className="text-[10px] text-muted-foreground mt-0.5 font-mono" title="Notional Value">
                  {fmt((parseFloat(execution.quantity) * parseFloat(execution.price) * execution.multiplier).toString())}
                </div>
              )}
            </>
          )}
        </td>

        {/* Commission */}
        <td className="px-3 py-2 text-sm text-right text-muted-foreground">
          {isEditing ? (
            <input
              type="number"
              value={editCommission}
              onChange={(e) => setEditCommission(e.target.value)}
              aria-label="Commission"
              className="w-20 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right font-mono"
            />
          ) : (
            <span className="cursor-pointer font-mono" onClick={() => setIsEditing(true)}>{fmt(execution.commission)}</span>
          )}
        </td>

        {/* P&L */}
        <td className="px-3 py-2 text-sm text-right">
          {isEditing ? (
            <input
              type="number"
              value={editPnl}
              placeholder="—"
              onChange={(e) => setEditPnl(e.target.value)}
              aria-label="P&L"
              className="w-24 px-1.5 py-0.5 text-xs border border-border rounded bg-background text-foreground text-right font-mono"
            />
          ) : (
            <span className="cursor-pointer" onClick={() => setIsEditing(true)}>{fmtPnl(execution.pnl)}</span>
          )}
        </td>

        {/* Lineage */}
        <td className="px-3 py-2 text-xs text-muted-foreground">
          {execution.parent_id ? (
            <span
              className="inline-flex items-center rounded border border-border bg-muted px-2 py-0.5 font-mono"
              title={`Parent execution: ${execution.parent_id}`}
            >
              {`↳ ${execution.parent_id.slice(0, 8)}`}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </td>

        {/* Status badge */}
        <td className="px-3 py-2">
          <div className="flex flex-col gap-1 items-start">
            <ExecutionStatusBadge
              origin={execution.origin}
              deleted={execution.deleted}
              user_modified={execution.user_modified}
              parent_id={execution.parent_id}
            />
            {isConflict && (
              <span className="inline-flex items-center rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-600 dark:text-amber-400" title="This execution is part of a conflict pair">
                Conflict
              </span>
            )}
          </div>
        </td>

         {/* Actions */}
         <td className="px-3 py-2 text-right">
           {isEditing ? (
             <div className="inline-flex items-center gap-1">
               <button
                 onClick={handleSave}
                 disabled={updateExecution.isPending || !editExecutedAt || !activePortfolioId}
                 className="p-1 rounded hover:bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-success disabled:opacity-50"
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
                    {canLinkBroker && onLinkBroker && (
                      <button
                        onClick={() => { setMenuOpen(false); onLinkBroker(execution); }}
                        className="w-full text-left px-3 py-1.5 text-xs hover:bg-muted text-foreground"
                      >
                        Link broker transaction…
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
                     className="w-full text-left px-3 py-1.5 text-xs hover:bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] text-danger"
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

      {errorMsg && (
        <tr>
          <td colSpan={colSpan ?? (trade.is_combo ? 13 : 10)} className="px-3 py-2 border-b border-border">
            <p className="text-xs text-destructive">{errorMsg}</p>
          </td>
        </tr>
      )}

      {showDeleteConfirm && (
        <tr>
          <td colSpan={colSpan ?? (trade.is_combo ? 13 : 10)} className="px-3 py-3 bg-[color-mix(in_srgb,var(--muted)_50%,transparent)] border-b border-border">
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
                  className="rounded bg-destructive px-2 py-1 text-destructive-foreground hover:opacity-90 disabled:opacity-50"
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
