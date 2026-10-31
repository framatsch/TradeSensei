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

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ArrowDown, ArrowUp, MoreHorizontal, Split, Undo2 } from "lucide-react";
import { useExecutionLegEditor } from "@/hooks/useExecutionLegEditor";
import type { LogicalExecution, Trade } from "@/lib/types";
import { ExecutionStatusBadge } from "./ExecutionStatusBadge";

interface Props {
  execution: LogicalExecution;
  trade: Trade;
  tradeId: string;
  onMoveToTrade?: (executionId: string) => void;
  onDetach?: (executionId: string) => void;
  onSplit?: (execution: LogicalExecution) => void;
  onLinkBroker?: (execution: LogicalExecution) => void;
  hasOptionLeg?: boolean;
  isConflict?: boolean;
}

interface SplitValueProps {
  asTraded: string;
  adjusted: string;
  currency?: boolean;
}

function formatNumber(value: string | null | undefined, currency = false): string {
  if (!value || !Number.isFinite(Number(value))) return "—";
  return `${currency ? "$" : ""}${Number(value).toLocaleString("en-US", { minimumFractionDigits: currency ? 2 : 0, maximumFractionDigits: 4 })}`;
}

function SplitValue({ asTraded, adjusted, currency = false }: SplitValueProps) {
  return (
    <>
      {formatNumber(asTraded, currency)}
      {Number(asTraded) !== Number(adjusted) && (
        <span className="ml-1 inline-flex items-center gap-0.5 text-muted-foreground" title={`The price chart shows this value as ${formatNumber(adjusted, currency)} (split-adjusted). The value above is as-traded.`}>
          (<Split size={12} aria-hidden="true" />{formatNumber(adjusted, currency)})
        </span>
      )}
    </>
  );
}

const MENU_ITEM = "cursor-pointer px-3 py-2.5 text-sm text-foreground outline-none data-[highlighted]:bg-muted";

export function ExecutionLegCard({ execution, trade, tradeId, onMoveToTrade, onDetach, onSplit, onLinkBroker, hasOptionLeg, isConflict }: Props) {
  const editor = useExecutionLegEditor(execution, tradeId);
  const {
    activePortfolioId, setIsEditing, isLong, isDeleted, canSplit, canLinkBroker,
    showDeleteConfirm, setShowDeleteConfirm, errorMsg, deleteExecution, restoreExecution,
    handleDelete, confirmDelete, handleRestore,
  } = editor;
  const pnl = execution.pnl === null ? null : Number(execution.pnl);

  return (
    <article
      data-testid="execution-leg-card"
      className={`solid-card min-w-0 p-4 ${isDeleted ? "opacity-50" : isConflict ? "border-l-[3px] border-l-warning bg-[color-mix(in_srgb,var(--warning)_10%,transparent)]" : ""}`}
    >
      {editor.isEditing && !isDeleted ? (
        <form onSubmit={editor.handleSave} noValidate aria-label="Edit execution" aria-busy={editor.updateExecution.isPending} className="space-y-3">
          <fieldset disabled={editor.updateExecution.isPending}>
            <legend className="mb-1 text-xs font-medium text-muted-foreground">Side</legend>
            <div className="flex gap-1 rounded-lg border border-border bg-muted p-1">
              <button type="button" aria-label="Set direction to LONG" aria-pressed={editor.editDirection === "LONG"} onClick={() => editor.setEditDirection("LONG")} className={`min-h-10 flex-1 rounded-md text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${editor.editDirection === "LONG" ? "bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-success" : "text-muted-foreground"}`}>BUY</button>
              <button type="button" aria-label="Set direction to SHORT" aria-pressed={editor.editDirection === "SHORT"} onClick={() => editor.setEditDirection("SHORT")} className={`min-h-10 flex-1 rounded-md text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${editor.editDirection === "SHORT" ? "bg-[color-mix(in_srgb,var(--danger)_15%,transparent)] text-danger" : "text-muted-foreground"}`}>SELL</button>
            </div>
          </fieldset>
          {[
            { key: "executed-at", label: "Executed at date and time", type: "datetime-local", value: editor.editExecutedAt, onChange: editor.setEditExecutedAt },
            { key: "quantity", label: "Quantity", type: "number", value: editor.editQty, onChange: editor.setEditQty },
            { key: "price", label: "Price", type: "number", value: editor.editPrice, onChange: editor.setEditPrice },
            { key: "commission", label: "Commission", type: "number", value: editor.editCommission, onChange: editor.setEditCommission },
            { key: "pnl", label: "P&L", type: "number", value: editor.editPnl, onChange: editor.setEditPnl },
          ].map((field) => (
            <div key={field.key}>
              <label htmlFor={`leg-${execution.id}-${field.key}`} className="mb-1 block text-xs font-medium text-muted-foreground">{field.label}</label>
              <input
                id={`leg-${execution.id}-${field.key}`}
                type={field.type}
                step={field.type === "number" ? "any" : undefined}
                value={field.value}
                onChange={(event) => field.onChange(event.target.value)}
                disabled={editor.updateExecution.isPending}
                required={field.key !== "pnl"}
                className="block min-h-10 w-full min-w-0 max-w-full rounded-md border border-border bg-secondary px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
            </div>
          ))}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={editor.handleCancel} disabled={editor.updateExecution.isPending} className="btn-ghost px-3 py-2 text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={editor.updateExecution.isPending || !editor.editExecutedAt || !activePortfolioId} className="btn-primary px-4 py-2 text-sm disabled:opacity-50">{editor.updateExecution.isPending ? "Saving..." : "Save"}</button>
          </div>
        </form>
      ) : (
      <>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${isLong ? "border-[color-mix(in_srgb,var(--success)_30%,transparent)] bg-[color-mix(in_srgb,var(--success)_15%,transparent)] text-success" : "border-[color-mix(in_srgb,var(--danger)_30%,transparent)] bg-[color-mix(in_srgb,var(--danger)_15%,transparent)] text-danger"}`} title={execution.direction}>
            {isLong ? <ArrowUp size={10} aria-hidden="true" /> : <ArrowDown size={10} aria-hidden="true" />}
            {isLong ? "BUY" : "SELL"}
          </span>
          <span className="min-w-0 break-words font-mono text-sm text-foreground">
            <SplitValue asTraded={execution.raw_quantity} adjusted={execution.quantity} /> @ <SplitValue asTraded={execution.raw_price} adjusted={execution.price} currency />
          </span>
        </div>
        {isDeleted ? (
          <button type="button" onClick={handleRestore} disabled={restoreExecution.isPending || !activePortfolioId} className="btn-ghost inline-flex min-h-10 shrink-0 items-center gap-1 px-2 text-xs disabled:opacity-50">
            <Undo2 size={12} aria-hidden="true" />
            {restoreExecution.isPending ? "Restoring..." : "Restore"}
          </button>
        ) : (
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button type="button" aria-label="Leg actions" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <MoreHorizontal size={18} aria-hidden="true" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content align="end" sideOffset={4} className="trade-mobile-contrast z-50 w-56 rounded-lg border border-border bg-popover py-1 shadow-lg">
                <DropdownMenu.Item onSelect={() => setIsEditing(true)} className={MENU_ITEM}>Edit</DropdownMenu.Item>
                {canSplit && onSplit && <DropdownMenu.Item onSelect={() => onSplit(execution)} className={MENU_ITEM}>Split</DropdownMenu.Item>}
                {canLinkBroker && onLinkBroker && <DropdownMenu.Item onSelect={() => onLinkBroker(execution)} className={MENU_ITEM}>Link broker transaction…</DropdownMenu.Item>}
                {onMoveToTrade && <DropdownMenu.Item onSelect={() => onMoveToTrade(execution.id)} className={MENU_ITEM}>Move to...</DropdownMenu.Item>}
                {onDetach && <DropdownMenu.Item onSelect={() => onDetach(execution.id)} className={MENU_ITEM}>Detach as new Trade</DropdownMenu.Item>}
                <DropdownMenu.Item onSelect={handleDelete} className="cursor-pointer px-3 py-2.5 text-sm text-danger outline-none data-[highlighted]:bg-[color-mix(in_srgb,var(--danger)_10%,transparent)]">Delete</DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        )}
      </div>

      <p className="mt-2 break-words font-mono text-xs text-muted-foreground">
        {new Date(execution.executed_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })} · Comm. {formatNumber(execution.commission, true)}
      </p>

      {trade.is_combo && (
        <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div className="min-w-0"><dt className="text-muted-foreground">Symbol</dt><dd className="break-words text-foreground">{execution.symbol}</dd></div>
          <div><dt className="text-muted-foreground">Asset Class</dt><dd className="text-foreground">{execution.asset_class}</dd></div>
          <div><dt className="text-muted-foreground">Open/Close</dt><dd className="text-foreground">{execution.open_close === "O" ? "Open" : execution.open_close === "C" ? "Close" : "—"}</dd></div>
        </dl>
      )}

      {(hasOptionLeg || execution.option_type) && (
        <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <div><dt className="text-muted-foreground">Strike</dt><dd className="font-mono text-foreground">{formatNumber(execution.strike, true)}</dd></div>
          <div><dt className="text-muted-foreground">Type</dt><dd className="text-foreground">{execution.option_type === "C" ? "Call" : execution.option_type === "P" ? "Put" : "—"}</dd></div>
          <div className="col-span-2"><dt className="text-muted-foreground">Expiry</dt><dd className="font-mono text-foreground">{execution.expiry ? new Date(`${execution.expiry}T12:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }) : "—"}</dd></div>
        </dl>
      )}

      {execution.multiplier !== 1 && (
        <p className="mt-2 break-words font-mono text-xs text-muted-foreground">
          Multiplier: {execution.multiplier} · Notional: {formatNumber(String(Number(execution.raw_quantity) * Number(execution.raw_price) * execution.multiplier), true)}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">
          P&amp;L <span className={`font-mono font-medium ${pnl === null || !Number.isFinite(pnl) ? "text-muted-foreground" : pnl >= 0 ? "text-success" : "text-danger"}`}>
            {pnl === null || !Number.isFinite(pnl) ? "—" : `${pnl >= 0 ? "+" : "-"}$${Math.abs(pnl).toFixed(2)}`}
          </span>
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          <ExecutionStatusBadge origin={execution.origin} deleted={execution.deleted} user_modified={execution.user_modified} parent_id={execution.parent_id} />
          {execution.parent_id && <span className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground" title={`Parent execution: ${execution.parent_id}`}>↳ {execution.parent_id.slice(0, 8)}</span>}
          {!isDeleted && execution.origin === "split" && execution.parent_id && <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground" title={`Proportionally allocated quantity from parent execution ${execution.parent_id}`}>Allocated</span>}
          {!isDeleted && isConflict && <span className="surface-warning rounded border px-1.5 py-0.5 text-[10px] text-warning">Conflict</span>}
        </div>
      </div>
      </>
      )}

      {showDeleteConfirm && (
        <div className="mt-3 space-y-3 border-t border-border pt-3 text-xs">
          <p className="text-foreground">Delete this execution? This will re-aggregate the trade.</p>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowDeleteConfirm(false)} disabled={deleteExecution.isPending} className="btn-ghost px-3 py-2 text-xs disabled:opacity-50">Cancel</button>
            <button type="button" onClick={confirmDelete} disabled={deleteExecution.isPending || !activePortfolioId} className="rounded-md border border-current bg-[color-mix(in_srgb,var(--danger)_10%,transparent)] px-3 py-2 text-xs text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50">{deleteExecution.isPending ? "Deleting..." : "Delete"}</button>
          </div>
        </div>
      )}
      {errorMsg && <p role="alert" className="mt-3 text-xs text-danger">{errorMsg}</p>}
    </article>
  );
}
