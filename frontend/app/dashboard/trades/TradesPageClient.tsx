/**
 * TradesPageClient — client component with filter, sort, selection, and bulk ops.
 */

"use client";

import { useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { TradeTable } from "@/components/trades/TradeTable";
import { TradeFilterBar } from "@/components/trades/TradeFilterBar";
import { BulkActionToolbar } from "@/components/trades/BulkActionToolbar";
import {
  useBulkDeleteTrades,
  useBulkAssignTag,
  useBulkAssignPlaybook,
} from "@/hooks/useTrades";
import type { TradeFilters, TradeSortConfig } from "@/hooks/useTrades";
import { useTags } from "@/hooks/useTags";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { TagBadge } from "@/components/tags/TagBadge";

// ─── URL helpers ─────────────────────────────────────────────────────────────

function readFiltersFromParams(params: URLSearchParams): TradeFilters {
  const pnlRaw = params.get("pnl_positive");
  let pnl_positive: boolean | null = null;
  if (pnlRaw === "true") pnl_positive = true;
  else if (pnlRaw === "false") pnl_positive = false;

  const assetClassRaw = params.get("asset_class");
  const tagIdsRaw = params.get("tag_ids");

  return {
    symbol: params.get("symbol") ?? undefined,
    direction: params.get("direction") ?? undefined,
    asset_classes: assetClassRaw ? assetClassRaw.split(",").filter(Boolean) : undefined,
    opened_at_from: params.get("opened_at_from") ?? undefined,
    opened_at_to: params.get("opened_at_to") ?? undefined,
    tag_ids: tagIdsRaw ? tagIdsRaw.split(",").filter(Boolean) : undefined,
    playbook_id: params.get("playbook_id") ?? undefined,
    pnl_positive,
  };
}

function readSortFromParams(params: URLSearchParams): TradeSortConfig {
  return {
    sort_by: params.get("sort_by") ?? undefined,
    sort_dir: (params.get("sort_dir") as "asc" | "desc") ?? undefined,
  };
}

function filtersToParams(
  filters: TradeFilters,
  sort: TradeSortConfig
): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.symbol) p.set("symbol", filters.symbol);
  if (filters.direction) p.set("direction", filters.direction);
  if (filters.asset_classes?.length) p.set("asset_class", filters.asset_classes.join(","));
  if (filters.opened_at_from) p.set("opened_at_from", filters.opened_at_from);
  if (filters.opened_at_to) p.set("opened_at_to", filters.opened_at_to);
  if (filters.tag_ids?.length) p.set("tag_ids", filters.tag_ids.join(","));
  if (filters.playbook_id) p.set("playbook_id", filters.playbook_id);
  if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) {
    p.set("pnl_positive", String(filters.pnl_positive));
  }
  if (sort.sort_by) p.set("sort_by", sort.sort_by);
  if (sort.sort_dir) p.set("sort_dir", sort.sort_dir);
  return p;
}

// ─── Tag picker modal ────────────────────────────────────────────────────────

interface TagPickerModalProps {
  onConfirm: (tagIds: string[]) => void;
  onCancel: () => void;
  isPending: boolean;
}

function TagPickerModal({ onConfirm, onCancel, isPending }: TagPickerModalProps) {
  const { data: tags } = useTags();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-base font-semibold text-slate-100 mb-4">Assign Tags</h2>
        <div className="flex flex-wrap gap-2 mb-6 min-h-12">
          {(tags ?? []).length === 0 && (
            <p className="text-slate-500 text-sm">No tags available.</p>
          )}
          {(tags ?? []).map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => toggle(tag.id)}
              className={`transition-opacity ${
                selected.has(tag.id)
                  ? "opacity-100 ring-2 ring-blue-500 ring-offset-1 ring-offset-slate-800 rounded-full"
                  : "opacity-50 hover:opacity-90"
              }`}
            >
              <TagBadge tag={tag} />
            </button>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-md text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={selected.size === 0 || isPending}
            onClick={() => onConfirm(Array.from(selected))}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-md text-sm"
          >
            {isPending ? "Saving…" : "Apply"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Playbook picker modal ────────────────────────────────────────────────────

interface PlaybookPickerModalProps {
  onConfirm: (playbookId: string | null) => void;
  onCancel: () => void;
  isPending: boolean;
}

function PlaybookPickerModal({ onConfirm, onCancel, isPending }: PlaybookPickerModalProps) {
  const { data: playbooks } = usePlaybooks();
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-base font-semibold text-slate-100 mb-4">Assign Playbook</h2>
        <div className="space-y-2 mb-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="playbook"
              value=""
              checked={selected === null}
              onChange={() => setSelected(null)}
              className="accent-blue-500"
            />
            <span className="text-sm text-slate-300">None</span>
          </label>
          {(playbooks ?? []).map((pb) => (
            <label key={pb.id} className="flex items-center gap-3 cursor-pointer">
              <input
                type="radio"
                name="playbook"
                value={pb.id}
                checked={selected === pb.id}
                onChange={() => setSelected(pb.id)}
                className="accent-blue-500"
              />
              <span className="text-sm text-slate-300">{pb.name}</span>
            </label>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-md text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => onConfirm(selected)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-md text-sm"
          >
            {isPending ? "Saving…" : "Apply"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── TradesPageClient ─────────────────────────────────────────────────────────

export function TradesPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [filters, setFilters] = useState<TradeFilters>(() =>
    readFiltersFromParams(searchParams)
  );
  const [sort, setSort] = useState<TradeSortConfig>(() =>
    readSortFromParams(searchParams)
  );
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showTagPicker, setShowTagPicker] = useState(false);
  const [showPlaybookPicker, setShowPlaybookPicker] = useState(false);

  const { mutate: bulkDelete, isPending: isDeleting } = useBulkDeleteTrades();
  const { mutate: bulkAssignTag, isPending: isAssigningTag } = useBulkAssignTag();
  const { mutate: bulkAssignPlaybook, isPending: isAssigningPlaybook } =
    useBulkAssignPlaybook();

  const pushToUrl = useCallback(
    (nextFilters: TradeFilters, nextSort: TradeSortConfig) => {
      const qs = filtersToParams(nextFilters, nextSort).toString();
      router.push(`/dashboard/trades${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router]
  );

  const handleFiltersChange = (nextFilters: TradeFilters) => {
    setFilters(nextFilters);
    pushToUrl(nextFilters, sort);
  };

  const handleSortChange = (nextSort: TradeSortConfig) => {
    setSort(nextSort);
    pushToUrl(filters, nextSort);
  };

  const handleDelete = () => {
    const count = selectedIds.size;
    if (
      !window.confirm(`Delete ${count} trade${count === 1 ? "" : "s"}? This cannot be undone.`)
    )
      return;
    bulkDelete(
      { trade_ids: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) }
    );
  };

  const handleTagConfirm = (tagIds: string[]) => {
    bulkAssignTag(
      { trade_ids: Array.from(selectedIds), tag_ids: tagIds },
      {
        onSuccess: () => {
          setSelectedIds(new Set());
          setShowTagPicker(false);
        },
      }
    );
  };

  const handlePlaybookConfirm = (playbookId: string | null) => {
    bulkAssignPlaybook(
      { trade_ids: Array.from(selectedIds), playbook_id: playbookId },
      {
        onSuccess: () => {
          setSelectedIds(new Set());
          setShowPlaybookPicker(false);
        },
      }
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <PageHeader title="Trades" subtitle="All recorded trading positions" />
        <Link
          href="/dashboard/trades/new"
          className="flex-shrink-0 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
        >
          + New Trade
        </Link>
      </div>

      <BulkActionToolbar
        selectedCount={selectedIds.size}
        onDelete={handleDelete}
        onAssignTag={() => setShowTagPicker(true)}
        onAssignPlaybook={() => setShowPlaybookPicker(true)}
        isDeleting={isDeleting}
      />

      <TradeFilterBar filters={filters} onChange={handleFiltersChange} />

      <TradeTable
        filters={filters}
        sort={sort}
        onSortChange={handleSortChange}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
      />

      {showTagPicker && (
        <TagPickerModal
          onConfirm={handleTagConfirm}
          onCancel={() => setShowTagPicker(false)}
          isPending={isAssigningTag}
        />
      )}

      {showPlaybookPicker && (
        <PlaybookPickerModal
          onConfirm={handlePlaybookConfirm}
          onCancel={() => setShowPlaybookPicker(false)}
          isPending={isAssigningPlaybook}
        />
      )}
    </div>
  );
}
