"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray, type SubmitHandler } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import type { Trade, TradeCreate, TradeUpdate, Direction, AssetClass, LogicalExecutionCreate } from "@/lib/types";
import { useCreateTrade, useUpdateTrade } from "@/hooks/useTrade";
import { useTags } from "@/hooks/useTags";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { useAccounts } from "@/hooks/useAccounts";
import { TagBadge } from "@/components/tags/TagBadge";
import { Spinner } from "@/components/ui/Spinner";
import { Trash2, Plus } from "lucide-react";
import { ExecutionSummaryCard } from "./ExecutionSummaryCard";

const DIRECTIONS: Direction[] = ["LONG", "SHORT"];
const ASSET_CLASSES: AssetClass[] = [
  "EQUITY",
  "OPTION",
  "FUTURE",
  "FOREX",
  "CRYPTO",
];

const legSchema = z.object({
  executed_at: z.string().min(1, "Date is required"),
  direction: z.enum(["LONG", "SHORT"]),
  quantity: z.string().min(1, "Quantity is required"),
  price: z.string().min(1, "Price is required"),
  commission: z.string().optional(),
});

const formSchema = z.object({
  symbol: z.string().min(1, "Symbol is required").transform(val => val.toUpperCase()),
  direction: z.enum(["LONG", "SHORT"]),
  is_combo: z.boolean().optional(),
  asset_class: z.enum(["EQUITY", "OPTION", "FUTURE", "FOREX", "CRYPTO"]).optional(),
  currency: z.string().max(3).optional().refine(val => !val || val.length === 3, "Currency must be a 3-letter ISO code"),
  account_id: z.string().optional(),
  
  quantity: z.string().optional(),
  entry_price: z.string().optional(),
  exit_price: z.string().optional(),
  pnl: z.string().optional(),
  stop_loss: z.string().optional().refine(val => !val || parseFloat(val) > 0, "Stop loss must be > 0 when provided"),
  take_profit: z.string().optional().refine(val => !val || parseFloat(val) > 0, "Take profit must be > 0 when provided"),
  commission: z.string().optional(),
  
  opened_at: z.string().optional(),
  closed_at: z.string().optional(),
  
  playbook_id: z.string().optional(),
  notes: z.string().optional(),
  user_rating: z.string().optional(),
  
  isAdvancedMode: z.boolean().optional(),
  executions: z.array(legSchema).optional(),
});

const createSchema = formSchema.refine(data => (data.is_combo ? true : Boolean(data.asset_class)), {
  message: "Asset class is required",
  path: ["asset_class"]
}).refine(data => (data.is_combo ? true : (data.quantity && parseFloat(data.quantity) > 0)), {
  message: "Quantity is required and must be > 0",
  path: ["quantity"]
}).refine(data => (data.is_combo ? true : (data.entry_price && parseFloat(data.entry_price) > 0)), {
  message: "Entry price is required and must be > 0",
  path: ["entry_price"]
}).refine(data => data.opened_at && data.opened_at.length > 0, {
  message: "Opened at is required",
  path: ["opened_at"]
});

type FormValues = z.infer<typeof formSchema>;

interface Props {
  trade?: Trade;
  onSuccess?: (trade: Trade) => void;
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

  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(
    trade?.tags.map((t) => t.id) ?? []
  );

  const { register, handleSubmit, control, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(isEditing ? formSchema : createSchema),
    defaultValues: isEditing ? {
      symbol: trade.symbol,
      direction: trade.direction,
      is_combo: trade.is_combo,
      asset_class: trade.asset_class ?? undefined,
      currency: trade.currency ?? "",
      account_id: trade.account_id ?? "",
      stop_loss: trade.stop_loss ?? "",
      take_profit: trade.take_profit ?? "",
      playbook_id: trade.playbook_id ?? "",
      notes: trade.notes ?? "",
      user_rating: trade.user_rating != null ? String(trade.user_rating) : "",
      isAdvancedMode: false,
      executions: [],
    } : {
      symbol: "",
      direction: "LONG",
      is_combo: false,
      asset_class: "EQUITY",
      currency: "",
      account_id: "",
      quantity: "",
      entry_price: "",
      exit_price: "",
      pnl: "",
      stop_loss: "",
      take_profit: "",
      commission: "0",
      opened_at: toLocalDatetimeValue(new Date().toISOString()),
      closed_at: "",
      playbook_id: "",
      notes: "",
      user_rating: "",
      isAdvancedMode: false,
      executions: [],
    }
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "executions"
  });

  const formValues = watch();
  const isAdvancedMode = formValues.isAdvancedMode;
  const executions = formValues.executions;
  const tradeDirection = formValues.direction;
  const isCombo = formValues.is_combo === true;
  const openedAt = formValues.opened_at;

  // Sync executions with main fields when in advanced mode
  useEffect(() => {
    console.log("Executions array:", JSON.stringify(executions));
    if (isAdvancedMode && executions && executions.length > 0) {
      // Find the first execution with a valid direction
      const firstExecutionWithDirection = executions.find(leg => leg && leg.direction);
      
      if (!firstExecutionWithDirection) {
        console.log("No executions with direction found yet");
        return;
      }
      
      let totalQty = 0;
      let totalValue = 0;
      let totalComm = 0;
      
      // Calculate based on first execution as entry
      const entryDirection = firstExecutionWithDirection.direction;
      let entryQty = 0;
      let entryValue = 0;
      
      executions.forEach(leg => {
        if (!leg) return;
        const legQty = parseFloat(leg.quantity) || 0;
        const legPrice = parseFloat(leg.price) || 0;
        const legComm = parseFloat(leg.commission || "0") || 0;
        
        totalComm += legComm;
        
        if (leg.direction === entryDirection) {
          entryQty += legQty;
          entryValue += legQty * legPrice;
        }
      });
      
      console.log("CALCULATED entryQty:", entryQty, "with direction:", entryDirection);
      
      if (entryQty > 0) {
        setValue("entry_price", (entryValue / entryQty).toFixed(4));
      }
      
      // Calculate current position (can be negative if over-closed)
      let currentQty = 0;
      executions.forEach(leg => {
        if (!leg) return;
        const legQty = parseFloat(leg.quantity) || 0;
        if (leg.direction === entryDirection) {
          currentQty += legQty;
        } else {
          currentQty -= legQty;
        }
      });
      
      // Max quantity is the max position size ever reached
      console.log("Setting quantity to:", entryQty.toString());
      setValue("quantity", entryQty.toString());
      setValue("commission", totalComm.toString());
      
      if (currentQty <= 0) {
        // Trade is closed or reversed
        // We could calculate exit price here, but let's keep it simple for now
      }
    }
  }, [isAdvancedMode, executions, setValue]);

  const createMutation = useCreateTrade();
  const updateMutation = useUpdateTrade(trade?.id ?? "");

  const isPending = isEditing ? updateMutation.isPending : createMutation.isPending;
  const mutError = isEditing ? updateMutation.error : createMutation.error;

  const serverError = (() => {
    if (!mutError) return null;
    const axiosErr = mutError as { response?: { data?: { detail?: string } } };
    return axiosErr.response?.data?.detail ?? mutError.message;
  })();

  const onSubmit: SubmitHandler<FormValues> = (data) => {
    const payloadBase = {
      symbol: data.symbol,
      direction: data.direction,
      is_combo: Boolean(data.is_combo),
      asset_class: data.is_combo ? undefined : (data.asset_class ?? null),
      quantity: data.is_combo ? null : (data.quantity ?? null),
      entry_price: data.is_combo ? null : (data.entry_price ?? null),
      exit_price: data.exit_price || null,
      stop_loss: data.stop_loss === "" ? null : data.stop_loss,
      take_profit: data.take_profit === "" ? null : data.take_profit,
      opened_at: toISOWithOffset(data.opened_at!) ?? new Date().toISOString(),
      closed_at: data.closed_at ? toISOWithOffset(data.closed_at) : null,
      pnl: data.pnl || null,
      commission: data.commission || "0",
      currency: data.currency?.toUpperCase() || null,
      notes: data.notes || null,
      user_rating: data.user_rating ? Number(data.user_rating) : null,
      playbook_id: data.playbook_id || null,
      tag_ids: selectedTagIds,
    };

    let payloadExecutions = null;
    if (data.isAdvancedMode && data.executions && data.executions.length > 0) {
      payloadExecutions = data.executions.map(leg => ({
        direction: leg.direction,
        quantity: leg.quantity,
        price: leg.price,
        commission: leg.commission || "0",
        executed_at: toISOWithOffset(leg.executed_at) ?? new Date().toISOString(),
      }));
    }

    if (isEditing) {
      const payload: TradeUpdate = {
        symbol: data.symbol,
        direction: data.direction,
        asset_class: data.asset_class,
        stop_loss: data.stop_loss === "" ? null : data.stop_loss,
        take_profit: data.take_profit === "" ? null : data.take_profit,
        notes: data.notes || null,
        user_rating: data.user_rating ? Number(data.user_rating) : null,
        playbook_id: data.playbook_id || null,
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
        ...payloadBase,
        account_id: data.account_id || null,
        executions: payloadExecutions,
      };
      createMutation.mutate(payload, {
        onSuccess: (created) => {
          if (onSuccess) onSuccess(created);
          else router.push(`/dashboard/trades/${created.id}`);
        },
      });
    }
  };

  function toggleTag(tagId: string) {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]
    );
  }

  const inputCls =
    "w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-zinc-500 disabled:opacity-50 disabled:cursor-not-allowed";
  const labelCls = "block text-xs font-medium text-muted-foreground mb-1";
  const errorCls = "text-xs text-red-400 mt-0.5";

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div id="debug-executions" style={{ display: 'none' }}>
        {JSON.stringify(executions)}
      </div>
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
              {...register("symbol")}
              placeholder="AAPL"
              className={inputCls}
              maxLength={20}
            />
            {errors.symbol && <p className={errorCls}>{errors.symbol.message}</p>}
          </div>

          <div>
            <label className={labelCls}>Direction *</label>
            <select
              {...register("direction")}
              className={inputCls}
            >
              {DIRECTIONS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {!isEditing && (
            <div className="sm:col-span-2 flex items-center gap-2">
              <input
                id="is_combo"
                type="checkbox"
                {...register("is_combo")}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              <label htmlFor="is_combo" className="text-sm text-foreground">COMBO position</label>
            </div>
          )}

          {(!isCombo || isEditing) && (
          <div>
            <label className={labelCls}>Asset Class *</label>
            <select
              {...register("asset_class")}
              className={inputCls}
            >
              {ASSET_CLASSES.map((ac) => (
                <option key={ac} value={ac}>{ac}</option>
              ))}
            </select>
          </div>
          )}

          <div>
            <label className={labelCls}>Currency (ISO-4217)</label>
            <input
              type="text"
              {...register("currency")}
              placeholder="USD"
              maxLength={3}
              className={inputCls}
            />
            {errors.currency && <p className={errorCls}>{errors.currency.message}</p>}
          </div>

          {!isEditing && accounts && accounts.length > 0 && (
            <div>
              <label className={labelCls}>Account</label>
              <select
                {...register("account_id")}
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

      {/* ── Advanced Mode Toggle ────────────────────────────────────────── */}
      <div className="flex items-center justify-between bg-card rounded-xl border border-border p-5">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Advanced Mode (Manual Legs)</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Build this trade by specifying individual execution legs.
          </p>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input 
            type="checkbox" 
            className="sr-only peer" 
            {...register("isAdvancedMode")}
          />
          <div className="w-11 h-6 bg-secondary peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
        </label>
      </div>

      {/* ── Execution Legs (Advanced Mode) ────────────────────────────────── */}
      {isAdvancedMode && (
        <div className="bg-card rounded-xl border border-border p-5 space-y-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Execution Legs</h3>
            <button
              type="button"
              onClick={() => append({ 
                executed_at: openedAt || toLocalDatetimeValue(new Date().toISOString()), 
                direction: tradeDirection, 
                quantity: "", 
                price: "", 
                commission: "0" 
              })}
              className="flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80"
            >
              <Plus className="w-4 h-4" /> Add Leg
            </button>
          </div>
          
          {fields.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4 border border-dashed border-border rounded-md">
              No execution legs added. Add a leg to calculate trade quantity and price.
            </p>
          ) : (
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div key={field.id} className="flex gap-2 items-start bg-secondary/50 p-3 rounded-lg border border-border">
                  <div className="grid grid-cols-5 gap-2 flex-1">
                    <div>
                      <label className={labelCls}>Date/Time</label>
                      <input
                        type="datetime-local"
                        {...register(`executions.${index}.executed_at` as const)}
                        className={inputCls}
                      />
                      {errors.executions?.[index]?.executed_at && <p className={errorCls}>{errors.executions[index]?.executed_at?.message}</p>}
                    </div>
                    <div>
                      <label className={labelCls}>Side</label>
                      <select
                        {...register(`executions.${index}.direction` as const)}
                        className={inputCls}
                      >
                        <option value="LONG">Buy</option>
                        <option value="SHORT">Sell</option>
                      </select>
                    </div>
                    <div>
                      <label className={labelCls}>Qty</label>
                      <input
                        type="number"
                        step="any"
                        min="0.000001"
                        {...register(`executions.${index}.quantity` as const)}
                        className={inputCls}
                      />
                      {errors.executions?.[index]?.quantity && <p className={errorCls}>{errors.executions[index]?.quantity?.message}</p>}
                    </div>
                    <div>
                      <label className={labelCls}>Price</label>
                      <input
                        type="number"
                        step="any"
                        min="0.000001"
                        {...register(`executions.${index}.price` as const)}
                        className={inputCls}
                      />
                      {errors.executions?.[index]?.price && <p className={errorCls}>{errors.executions[index]?.price?.message}</p>}
                    </div>
                    <div>
                      <label className={labelCls}>Fees</label>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        {...register(`executions.${index}.commission` as const)}
                        className={inputCls}
                      />
                    </div>
                  </div>
                  <div className="pt-6">
                    <button
                      type="button"
                      onClick={() => remove(index)}
                      className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-md transition-colors"
                      title="Remove leg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Section 2: Entry / Exit ───────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Entry / Exit</h3>
        {isEditing && trade && (
          <div className="mb-6">
            <ExecutionSummaryCard trade={trade} executions={trade.legs || []} />
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {!isEditing && (
            <>
              <div>
                <label className={labelCls}>Quantity *</label>
                <input
                  type="number"
                  step="any"
                  min="0.000001"
                  {...register("quantity")}
                  disabled={isAdvancedMode}
                  className={inputCls}
                />
                {errors.quantity && <p className={errorCls}>{errors.quantity.message}</p>}
              </div>

              <div>
                <label className={labelCls}>Entry Price *</label>
                <input
                  type="number"
                  step="any"
                  min="0.000001"
                  {...register("entry_price")}
                  disabled={isAdvancedMode}
                  className={inputCls}
                />
                {errors.entry_price && <p className={errorCls}>{errors.entry_price.message}</p>}
              </div>

              <div>
                <label className={labelCls}>Exit Price</label>
                <input
                  type="number"
                  step="any"
                  min="0.000001"
                  {...register("exit_price")}
                  disabled={isAdvancedMode}
                  placeholder="Leave blank for open trade"
                  className={inputCls}
                />
                {errors.exit_price && <p className={errorCls}>{errors.exit_price.message}</p>}
              </div>

              <div>
                <label className={labelCls}>PnL</label>
                <input
                  type="number"
                  step="any"
                  {...register("pnl")}
                  placeholder="Realised PnL"
                  className={inputCls}
                />
              </div>
            </>
          )}

          <div>
            <label className={labelCls}>
              Stop Loss{" "}
              <span className="text-muted-foreground font-normal">(leave blank to clear)</span>
            </label>
            <input
              type="number"
              step="any"
              min="0.000001"
              {...register("stop_loss")}
              placeholder="None"
              className={inputCls}
            />
            {errors.stop_loss && <p className={errorCls}>{errors.stop_loss.message}</p>}
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
              {...register("take_profit")}
              placeholder="None"
              className={inputCls}
            />
            {errors.take_profit && <p className={errorCls}>{errors.take_profit.message}</p>}
          </div>

          {!isEditing && (
            <div>
              <label className={labelCls}>Commission</label>
              <input
                type="number"
                step="any"
                min="0"
                {...register("commission")}
                disabled={isAdvancedMode}
                className={inputCls}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Section 3: Timestamps ─────────────────────────────────────────── */}
      {!isEditing && (
        <div className="bg-card rounded-xl border border-border p-5">
          <h3 className="text-sm font-semibold text-muted-foreground mb-4">Timestamps (UTC)</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Opened At *</label>
              <input
                type="datetime-local"
                {...register("opened_at")}
                className={inputCls}
              />
              {errors.opened_at && <p className={errorCls}>{errors.opened_at.message}</p>}
            </div>

            <div>
              <label className={labelCls}>Closed At</label>
              <input
                type="datetime-local"
                {...register("closed_at")}
                className={inputCls}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── Section 4: Tags & Playbook ────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-muted-foreground mb-4">Tags &amp; Playbook</h3>

        <div className="mb-4">
          <label className={labelCls}>Playbook</label>
          <select
            {...register("playbook_id")}
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
        <div className="mb-4 max-w-xs">
          <label className={labelCls}>User Rating (1-5)</label>
          <input
            type="number"
            min="1"
            max="5"
            step="1"
            {...register("user_rating")}
            className={inputCls}
            placeholder="Optional"
          />
        </div>
        <textarea
          {...register("notes")}
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
            className="px-4 py-2 text-sm text-muted-foreground bg-secondary hover:bg-zinc-200 dark:bg-zinc-600 disabled:opacity-50 rounded-md transition-colors"
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
