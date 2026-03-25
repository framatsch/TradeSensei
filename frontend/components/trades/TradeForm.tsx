/**
 * TradeForm — shared create/edit form for trades.
 * In create mode: all fields start empty, calls useCreateTrade on submit.
 * In edit mode: fields pre-populated from trade, calls useUpdateTrade on submit.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Trade, TradeCreate, TradeUpdate, Direction, AssetClass } from "@/lib/types";
import { useCreateTrade, useUpdateTrade } from "@/hooks/useTrade";
import { useTags } from "@/hooks/useTags";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useAccounts } from "@/hooks/useAccounts";
import { TagBadge } from "@/components/tags/TagBadge";
import { Spinner } from "@/components/ui/Spinner";
import type { AxiosError } from "axios";

const DIRECTIONS: Direction[] = ["LONG", "SHORT"];
const ASSET_CLASSES: AssetClass[] = [
  "EQUITY",
  "OPTION",
  "FUTURE",
  "FOREX",
  "CRYPTO",
];

interface Props {
  /** When provided, the form operates in edit mode. */
  trade?: Trade;
  /** Called after successful save (create or update). */
  onSuccess?: (trade: Trade) => void;
  /** Called when user clicks Cancel. */
  onCancel?: () => void;
}

function toLocalDatetimeValue(isoString: string | null | undefined): string {
  if (!isoString) return "";
  const d = new Date(isoString);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function toISOWithOffset(localDatetime: string): string | null {
  if (!localDatetime) return null;
  return new Date(localDatetime + ":00Z").toISOString();
}

export function TradeForm({ trade, onSuccess, onCancel }: Props) {
  const isEditing = trade !== undefined;
  const router = useRouter();

  const { data: allTags } = useTags();
  const { data: playbooks } = usePlaybooks();
  const { data: accounts } = useAccounts();

  // ── Form state ────────────────────────────────────────────────────────────
  const [symbol, setSymbol] = useState(trade?.symbol ?? "");
  const [direction, setDirection] = useState<Direction>(trade?.direction ?? "LONG");
  const [assetClass, setAssetClass] = useState<AssetClass>(trade?.asset_class ?? "EQUITY");
  const [quantity, setQuantity] = useState(trade?.quantity ?? "");
  const [entryPrice, setEntryPrice] = useState(trade?.entry_price ?? "");
  const [exitPrice, setExitPrice] = useState(trade?.exit_price ?? "");
  const [stopLoss, setStopLoss] = useState(trade?.stop_loss ?? "");
  const [takeProfit, setTakeProfit] = useState(trade?.take_profit ?? "");
  const [openedAt, setOpenedAt] = useState(toLocalDatetimeValue(trade?.opened_at));
  const [closedAt, setClosedAt] = useState(toLocalDatetimeValue(trade?.closed_at));
  const [pnl, setPnl] = useState(trade?.pnl ?? "");
  const [commission, setCommission] = useState(trade?.commission ?? "0");
  const [currency, setCurrency] = useState(trade?.currency ?? "");
  const [notes, setNotes] = useState(trade?.notes ?? "");
  const [playbookId, setPlaybookId] = useState<string>(trade?.playbook_id ?? "");
  const [accountId, setAccountId] = useState<string>("");
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(
    trade?.tags.map((t) => t.id) ?? []
  );

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createMutation = useCreateTrade();
  const updateMutation = useUpdateTrade(trade?.id ?? "");

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutError = isEditing ? updateMutation.error : createMutation.error;

  const serverError = (() => {
    if (!mutError) return null;
    const axiosErr = mutError as AxiosError<{ detail?: string }>;
    return axiosErr.response?.data?.detail ?? mutError.message;
  })();

  // ── Validation ────────────────────────────────────────────────────────────
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!symbol.trim()) errs.symbol = "Symbol is required.";
    if (!quantity || parseFloat(quantity) <= 0) errs.quantity = "Quantity must be > 0.";
    if (!entryPrice || parseFloat(entryPrice) <= 0) errs.entry_price = "Entry price must be > 0.";
    if (exitPrice && parseFloat(exitPrice) <= 0) errs.exit_price = "Exit price must be > 0 when provided.";
    if (stopLoss && parseFloat(stopLoss) <= 0) errs.stop_loss = "Stop loss must be > 0 when provided.";
    if (takeProfit && parseFloat(takeProfit) <= 0) errs.take_profit = "Take profit must be > 0 when provided.";
    if (!openedAt) errs.opened_at = "Opened at is required.";
    if (currency && currency.length !== 3) errs.currency = "Currency must be a 3-letter ISO code.";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!validate()) return;

    if (isEditing) {
      const payload: TradeUpdate = {
        symbol: symbol.trim(),
        direction,
        asset_class: assetClass,
        quantity,
        entry_price: entryPrice,
        exit_price: exitPrice || null,
        stop_loss: stopLoss === "" ? null : stopLoss,
        take_profit: takeProfit === "" ? null : takeProfit,
        opened_at: toISOWithOffset(openedAt),
        closed_at: closedAt ? toISOWithOffset(closedAt) : null,
        pnl: pnl || null,
        commission,
        currency: currency.trim() || null,
        notes: notes.trim() || null,
        playbook_id: playbookId || null,
        tag_ids: selectedTagIds,
      };
      updateMutation.mutate(payload, {
        onSuccess: (updated) => {
          if (onSuccess) onSuccess(updated);
          else router.push(`/dashboard/trades/${updated.id}`);
        },
      });
    } else {
      const payload: TradeCreate = {
        symbol: symbol.trim(),
        direction,
        asset_class: assetClass,
        quantity,
        entry_price: entryPrice,
        exit_price: exitPrice || null,
        stop_loss: stopLoss || null,
        take_profit: takeProfit || null,
        opened_at: toISOWithOffset(openedAt) ?? new Date().toISOString(),
        closed_at: closedAt ? toISOWithOffset(closedAt) : null,
        pnl: pnl || null,
        commission: commission || "0",
        currency: currency.trim() || null,
        notes: notes.trim() || null,
        account_id: accountId || null,
        playbook_id: playbookId || null,
        tag_ids: selectedTagIds,
      };
      createMutation.mutate(payload, {
        onSuccess: (created) => {
          if (onSuccess) onSuccess(created);
          else router.push(`/dashboard/trades/${created.id}`);
        },
      });
    }
  }

  function toggleTag(tagId: string) {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );
  }

  const inputCls =
    "w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-slate-500";
  const labelCls = "block text-xs font-medium text-muted-foreground mb-1";
  const errorCls = "text-xs text-red-400 mt-0.5";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {serverError && (
        <p className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
          {serverError}
        </p>
      )}

      {/* ── Section 1: Instrument ─────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Instrument</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Symbol *</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="AAPL"
              className={inputCls}
              maxLength={20}
            />
            {errors.symbol && <p className={errorCls}>{errors.symbol}</p>}
          </div>

          <div>
            <label className={labelCls}>Direction *</label>
            <select
              value={direction}
              onChange={(e) => setDirection(e.target.value as Direction)}
              className={inputCls}
            >
              {DIRECTIONS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Asset Class *</label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value as AssetClass)}
              className={inputCls}
            >
              {ASSET_CLASSES.map((ac) => (
                <option key={ac} value={ac}>{ac}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>Currency (ISO-4217)</label>
            <input
              type="text"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              placeholder="USD"
              maxLength={3}
              className={inputCls}
            />
            {errors.currency && <p className={errorCls}>{errors.currency}</p>}
          </div>

          {!isEditing && accounts && accounts.length > 0 && (
            <div>
              <label className={labelCls}>Account</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className={inputCls}
              >
                <option value="">— None —</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* ── Section 2: Entry / Exit ───────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Entry / Exit</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Quantity *</label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className={inputCls}
            />
            {errors.quantity && <p className={errorCls}>{errors.quantity}</p>}
          </div>

          <div>
            <label className={labelCls}>Entry Price *</label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              className={inputCls}
            />
            {errors.entry_price && <p className={errorCls}>{errors.entry_price}</p>}
          </div>

          <div>
            <label className={labelCls}>Exit Price</label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={exitPrice}
              onChange={(e) => setExitPrice(e.target.value)}
              placeholder="Leave blank for open trade"
              className={inputCls}
            />
            {errors.exit_price && <p className={errorCls}>{errors.exit_price}</p>}
          </div>

          <div>
            <label className={labelCls}>PnL</label>
            <input
              type="number"
              step="any"
              value={pnl}
              onChange={(e) => setPnl(e.target.value)}
              placeholder="Realised PnL"
              className={inputCls}
            />
          </div>

          <div>
            <label className={labelCls}>
              Stop Loss{" "}
              <span className="text-muted-foreground font-normal">(leave blank to clear)</span>
            </label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              placeholder="None"
              className={inputCls}
            />
            {errors.stop_loss && <p className={errorCls}>{errors.stop_loss}</p>}
          </div>

          <div>
            <label className={labelCls}>
              Take Profit{" "}
              <span className="text-muted-foreground font-normal">(leave blank to clear)</span>
            </label>
            <input
              type="number"
              step="any"
              min="0.000001"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              placeholder="None"
              className={inputCls}
            />
            {errors.take_profit && <p className={errorCls}>{errors.take_profit}</p>}
          </div>

          <div>
            <label className={labelCls}>Commission</label>
            <input
              type="number"
              step="any"
              min="0"
              value={commission}
              onChange={(e) => setCommission(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>
      </div>

      {/* ── Section 3: Timestamps ─────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Timestamps (UTC)</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Opened At *</label>
            <input
              type="datetime-local"
              value={openedAt}
              onChange={(e) => setOpenedAt(e.target.value)}
              className={inputCls}
            />
            {errors.opened_at && <p className={errorCls}>{errors.opened_at}</p>}
          </div>

          <div>
            <label className={labelCls}>Closed At</label>
            <input
              type="datetime-local"
              value={closedAt}
              onChange={(e) => setClosedAt(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>
      </div>

      {/* ── Section 4: Tags & Playbook ────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Tags &amp; Playbook</h3>

        <div className="mb-4">
          <label className={labelCls}>Playbook</label>
          <select
            value={playbookId}
            onChange={(e) => setPlaybookId(e.target.value)}
            className={inputCls}
          >
            <option value="">— None —</option>
            {(playbooks ?? []).map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelCls}>Tags</label>
          {!allTags ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Spinner size="sm" /> Loading tags…
            </div>
          ) : allTags.length === 0 ? (
            <p className="text-xs text-muted-foreground">No tags created yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2 mt-1">
              {allTags.map((tag) => {
                const selected = selectedTagIds.includes(tag.id);
                return (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => toggleTag(tag.id)}
                    className={`transition-opacity ${
                      selected ? "opacity-100" : "opacity-40 hover:opacity-70"
                    }`}
                    aria-pressed={selected}
                  >
                    <TagBadge tag={tag} />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Section 5: Notes ──────────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Notes</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          placeholder="Trade rationale, emotional state, post-trade review…"
          className={`${inputCls} resize-y`}
          maxLength={10000}
        />
      </div>

      {/* ── Actions ───────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 justify-end">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 text-sm text-muted-foreground bg-secondary hover:bg-slate-200 dark:bg-slate-600 disabled:opacity-50 rounded-md transition-colors"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={isPending}
          className="flex items-center gap-2 px-5 py-2 text-sm text-white bg-primary hover:bg-primary/90 disabled:opacity-50 rounded-md transition-colors font-medium"
        >
          {isPending && <Spinner size="sm" />}
          {isPending
            ? isEditing ? "Saving…" : "Creating…"
            : isEditing ? "Save Changes" : "Create Trade"}
        </button>
      </div>
    </form>
  );
}
