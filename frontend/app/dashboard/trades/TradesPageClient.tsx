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
 * TradesPageClient — client component with filter, sort, selection, and bulk ops.
 */

"use client";

import { useState, useCallback, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Plus, X } from "lucide-react";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { SaveFilterModal } from "@/components/trades/SaveFilterModal";
import { TradeTable } from "@/components/trades/TradeTable";
import { TradeFilterBar } from "@/components/trades/TradeFilterBar";
import { BulkActionToolbar } from "@/components/trades/BulkActionToolbar";
import {
  useBulkDeleteTrades,
  useBulkAssignTaxonomy,
  useBulkAssignPlaybook,
} from "@/hooks/useTrades";
import type { TradeFilters, TradeSortConfig } from "@/hooks/useTrades";
import {
  useSavedTradeFilters,
  useDeleteSavedTradeFilter,
  useUpdateSavedTradeFilter,
} from "@/hooks/useSavedTradeFilters";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import { TaxonomyBadge } from "@/components/trades/TaxonomyBadge";
import { useSettings } from "@/hooks/useSettings";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import { buildDefinitionFromFilters } from "@/lib/tradeFilterUtils";
import type { DefaultDateRange, SavedTradeFilterRead, Trade } from "@/lib/types";
import { MergePreviewModal } from "@/components/trades/MergePreviewModal";


const EMPTY_FILTERS: TradeFilters = {
  symbols: [],
  excluded_symbols: [],
  direction: "",
  asset_classes: [],
  opened_at_from: "",
  opened_at_to: "",
  closed_at_from: "",
  closed_at_to: "",
  taxonomy_ids: [],
  account_ids: [],
  playbook_id: "",
  pnl_positive: null,
  status: null,
  hour_of_day: undefined,
  day_of_week: undefined,
  annotation_filters: [],
};

// ─── Date range helpers ───────────────────────────────────────────────────────

function dateRangeToFrom(range: DefaultDateRange): string | undefined {
  const now = new Date();
  if (range === "last30") {
    const d = new Date(now);
    d.setDate(d.getDate() - 30);
    return d.toISOString().slice(0, 10);
  }
  if (range === "ytd") {
    return `${now.getFullYear()}-01-01`;
  }
  return undefined; // "all" — no filter
}

// ─── URL helpers ─────────────────────────────────────────────────────────────

function readFiltersFromParams(params: URLSearchParams): TradeFilters {
  const pnlRaw = params.get("pnl_positive");
  let pnl_positive: boolean | null = null;
  if (pnlRaw === "true") pnl_positive = true;
  else if (pnlRaw === "false") pnl_positive = false;

  const assetClassRaw = params.get("asset_class");
  const taxonomyIdsRaw = params.get("taxonomy_ids");
  const accountIdsRaw = params.get("account_ids");
  const legacyAccountId = params.get("account_id");

  const statusRaw = params.get("status");
  const status: "open" | "closed" | "all" | null =
    statusRaw === "open" || statusRaw === "closed" || statusRaw === "all" ? statusRaw : null;

  const hourRaw = params.get("hour_of_day");
  const dowRaw = params.get("day_of_week");

  return {
    symbols: params.get("symbols") ? params.get("symbols")!.split(",").filter(Boolean) : (params.get("symbol") ? params.get("symbol")!.split(",").filter(Boolean) : undefined),
    excluded_symbols: params.get("excluded_symbols") ? params.get("excluded_symbols")!.split(",").filter(Boolean) : undefined,
    direction: params.get("direction") ?? undefined,
    asset_classes: assetClassRaw ? assetClassRaw.split(",").filter(Boolean) : undefined,
    opened_at_from: params.get("opened_at_from") ?? undefined,
    opened_at_to: params.get("opened_at_to") ?? undefined,
    closed_at_from: params.get("closed_at_from") ?? undefined,
    closed_at_to: params.get("closed_at_to") ?? undefined,
    taxonomy_ids: taxonomyIdsRaw ? taxonomyIdsRaw.split(",").filter(Boolean) : undefined,
    account_ids: accountIdsRaw
      ? accountIdsRaw.split(",").filter(Boolean)
      : legacyAccountId
      ? [legacyAccountId]
      : undefined,
    playbook_id: params.get("playbook_id") ?? undefined,
    pnl_positive,
    status: status === "all" ? null : status,
    hour_of_day: hourRaw !== null ? parseInt(hourRaw, 10) : undefined,
    day_of_week: dowRaw !== null ? parseInt(dowRaw, 10) : undefined,
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
  sort: TradeSortConfig,
  limit: number,
  viewId?: string
): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.symbols?.length) p.set("symbols", filters.symbols.join(","));
  if (filters.excluded_symbols?.length) p.set("excluded_symbols", filters.excluded_symbols.join(","));
  if (filters.direction) p.set("direction", filters.direction);
  if (filters.asset_classes?.length) p.set("asset_class", filters.asset_classes.join(","));
  if (filters.opened_at_from) p.set("opened_at_from", filters.opened_at_from);
  if (filters.opened_at_to) p.set("opened_at_to", filters.opened_at_to);
  if (filters.closed_at_from) p.set("closed_at_from", filters.closed_at_from);
  if (filters.closed_at_to) p.set("closed_at_to", filters.closed_at_to);
  if (filters.taxonomy_ids?.length) p.set("taxonomy_ids", filters.taxonomy_ids.join(","));
  if (filters.account_ids?.length) p.set("account_ids", filters.account_ids.join(","));
  if (filters.playbook_id) p.set("playbook_id", filters.playbook_id);
  if (filters.pnl_positive !== null && filters.pnl_positive !== undefined) {
    p.set("pnl_positive", String(filters.pnl_positive));
  }
  if (filters.status) p.set("status", filters.status);
  if (filters.hour_of_day !== undefined && filters.hour_of_day !== null) {
    p.set("hour_of_day", String(filters.hour_of_day));
  }
  if (filters.day_of_week !== undefined && filters.day_of_week !== null) {
    p.set("day_of_week", String(filters.day_of_week));
  }
  if (sort.sort_by) p.set("sort_by", sort.sort_by);
  if (sort.sort_dir) p.set("sort_dir", sort.sort_dir);
  if (limit !== 20) p.set("limit", String(limit));
  // view_id is preserved when sorting/paging, cleared when filters change manually
  if (viewId) p.set("view_id", viewId);
  return p;
}

// ─── Taxonomy picker modal ───────────────────────────────────────────────────

interface TaxonomyPickerModalProps {
  onConfirm: (taxonomyIds: string[]) => void;
  onCancel: () => void;
  isPending: boolean;
}

function TaxonomyPickerModal({ onConfirm, onCancel, isPending }: TaxonomyPickerModalProps) {
  const { data: taxonomies } = useGetTaxonomies("trades");
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
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-base font-semibold text-foreground mb-4">Assign Taxonomies</h2>
        <div className="flex flex-wrap gap-2 mb-6 min-h-12">
          {(taxonomies ?? []).length === 0 && (
            <p className="text-muted-foreground text-sm">No taxonomies available.</p>
          )}
          {(taxonomies ?? []).map((taxonomy) => (
            <button
              key={taxonomy.id}
              type="button"
              onClick={() => toggle(taxonomy.id)}
              className={`transition-opacity ${
                selected.has(taxonomy.id)
                  ? "opacity-100 ring-2 ring-primary ring-offset-1 ring-offset-background rounded-full"
                  : "opacity-50 hover:opacity-90"
              }`}
            >
              <TaxonomyBadge taxonomy={taxonomy} />
            </button>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-secondary hover:bg-muted text-muted-foreground rounded-md text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={selected.size === 0 || isPending}
            onClick={() => onConfirm(Array.from(selected))}
            className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-md text-sm"
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
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm shadow-2xl">
        <h2 className="text-base font-semibold text-foreground mb-4">Assign Playbook</h2>
        <div className="space-y-2 mb-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="playbook"
              value=""
              checked={selected === null}
              onChange={() => setSelected(null)}
              className="accent-primary"
            />
            <span className="text-sm text-muted-foreground">None</span>
          </label>
          {(playbooks ?? []).map((pb) => (
            <label key={pb.id} className="flex items-center gap-3 cursor-pointer">
              <input
                type="radio"
                name="playbook"
                value={pb.id}
                checked={selected === pb.id}
                onChange={() => setSelected(pb.id)}
                className="accent-primary"
              />
              <span className="text-sm text-muted-foreground">{pb.name}</span>
            </label>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-secondary hover:bg-muted text-muted-foreground rounded-md text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => onConfirm(selected)}
            className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white rounded-md text-sm"
          >
            {isPending ? "Saving…" : "Apply"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Rename view modal ────────────────────────────────────────────────────────

interface RenameViewModalProps {
  currentName: string;
  onSave: (name: string) => void;
  onClose: () => void;
  isPending: boolean;
}

function RenameViewModal({ currentName, onSave, onClose, isPending }: RenameViewModalProps) {
  const [name, setName] = useState(currentName);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-card border border-border p-6 shadow-2xl">
        <h2 className="mb-4 text-base font-semibold text-foreground">Rename View</h2>
        <input
          type="text"
          className="w-full rounded-lg border border-border bg-secondary px-4 py-2 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && name.trim() && onSave(name.trim())}
          autoFocus
        />
        <div className="mt-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!name.trim() || isPending}
            onClick={() => name.trim() && onSave(name.trim())}
            className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors"
          >
            {isPending ? "Saving…" : "Save"}
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
  const { data: settings, isPlaceholderData: isSettingsLoading } = useSettings();
  const showOpenTrades = useShowOpenTrades();
  const enforceClosedStatus = !isSettingsLoading && !showOpenTrades;
  const { activePortfolioId } = useActivePortfolio();

  // Active view ID is read reactively from the URL (set by sidebar navigation).
  const activeViewId = searchParams.get("view_id") ?? undefined;

  // If no URL date params are present, apply the user's default_date_range setting.
  const hasUrlDateParams =
    searchParams.has("opened_at_from") ||
    searchParams.has("opened_at_to") ||
    searchParams.has("closed_at_from") ||
    searchParams.has("closed_at_to");

  const [filters, setFilters] = useState<TradeFilters>(() => {
    const fromParams = readFiltersFromParams(searchParams);
    if (!hasUrlDateParams && settings?.default_date_range && settings.default_date_range !== "all") {
      fromParams.opened_at_from = dateRangeToFrom(settings.default_date_range);
    }
    return fromParams;
  });
  const [sort, setSort] = useState<TradeSortConfig>(() =>
    readSortFromParams(searchParams)
  );
  const [limit, setLimit] = useState<number>(() => {
    const raw = searchParams.get("limit");
    const parsed = raw ? parseInt(raw, 10) : NaN;
    return [10, 20, 50, 100].includes(parsed) ? parsed : 20;
  });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedTrades, setSelectedTrades] = useState<Trade[]>([]);
  const [showTaxonomyPicker, setShowTaxonomyPicker] = useState(false);
  const [showPlaybookPicker, setShowPlaybookPicker] = useState(false);
  const [showSaveFilter, setShowSaveFilter] = useState(false);
  const [showRenameView, setShowRenameView] = useState(false);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [openStatusBlockedHint, setOpenStatusBlockedHint] = useState(false);

  const requestedOpenStatus = (searchParams.get("status") ?? null) === "open";
  const enforcedStatus = enforceClosedStatus ? "closed" : filters.status;

  useEffect(() => {
    if (showOpenTrades) {
      setBannerDismissed(false);
      setOpenStatusBlockedHint(false);
    }
  }, [showOpenTrades]);

  // Strip stale ?status=open once we know the real setting disallows open trades.
  // Uses enforceClosedStatus (not showOpenTrades) so cleanup only fires after
  // settings have loaded — avoids incorrectly wiping params during placeholder phase.
  useEffect(() => {
    if (enforceClosedStatus && requestedOpenStatus) {
      setOpenStatusBlockedHint(true);
      setBannerDismissed(false);
      const params = new URLSearchParams(searchParams.toString());
      params.delete("status");
      const qs = params.toString();
      router.replace(`/dashboard/trades${qs ? `?${qs}` : ""}`, { scroll: false });
    }
  }, [enforceClosedStatus, requestedOpenStatus, searchParams, router]);

  // Sync filters state when URL changes externally (e.g. sidebar view navigation).
  useEffect(() => {
    setFilters(readFiltersFromParams(searchParams));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.toString()]);

  // Resolve the full active view object (needed to know scope for Update/Delete).
  const { data: savedViews } = useSavedTradeFilters();
  const activeView: SavedTradeFilterRead | undefined = activeViewId
    ? savedViews?.find((v) => v.id === activeViewId)
    : undefined;

  const { mutate: bulkDelete, isPending: isDeleting } = useBulkDeleteTrades();
  const { mutate: bulkAssignTaxonomy, isPending: isAssigningTaxonomy } = useBulkAssignTaxonomy();
  const { mutate: bulkAssignPlaybook, isPending: isAssigningPlaybook } =
    useBulkAssignPlaybook();
  const { mutate: deleteFilter } = useDeleteSavedTradeFilter();
  // Hook requires id at call time; falls back to "" when no view is active (mutation never fires).
  const { mutate: updateFilter, isPending: isUpdating } = useUpdateSavedTradeFilter(
    activeViewId ?? ""
  );

  const pushToUrl = useCallback(
    (nextFilters: TradeFilters, nextSort: TradeSortConfig, nextLimit: number, viewId?: string) => {
      const qs = filtersToParams(nextFilters, nextSort, nextLimit, viewId).toString();
      router.push(`/dashboard/trades${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [router]
  );

  // Manual filter change — keep view_id so the user can still Update/Rename the view.
  const handleFiltersChange = (nextFilters: TradeFilters) => {
    setFilters(nextFilters);
    pushToUrl(nextFilters, sort, limit, activeViewId);
  };

  // Sort / limit changes → preserve active view_id.
  const handleSortChange = (nextSort: TradeSortConfig) => {
    setSort(nextSort);
    pushToUrl(filters, nextSort, limit, activeViewId);
  };

  const handleLimitChange = (nextLimit: number) => {
    setLimit(nextLimit);
    pushToUrl(filters, sort, nextLimit, activeViewId);
  };

  // Delete the currently active user view.
  const handleDeleteView = () => {
    if (!activeViewId) return;
    if (!window.confirm("Delete this saved view?")) return;
    deleteFilter(activeViewId, {
      onSuccess: () => {
        // Keep filters active, just remove the view reference.
        pushToUrl(filters, sort, limit);
      },
    });
  };

  // Overwrite the currently active user view with the current filters.
  const handleUpdateView = () => {
    if (!activeViewId) return;
    const definition = buildDefinitionFromFilters(filters);
    updateFilter({ definition });
    // view_id stays in URL — no pushToUrl call needed.
  };

  // Rename the currently active user view — view_id stays selected.
  const handleRenameView = (newName: string) => {
    if (!activeViewId) return;
    updateFilter({ name: newName }, {
      onSuccess: () => setShowRenameView(false),
    });
  };

  const handleDelete = () => {
    const count = selectedIds.size;
    if (
      !window.confirm(`Delete ${count} trade${count === 1 ? "" : "s"}? This cannot be undone.`)
    )
      return;
    bulkDelete(
      { trade_ids: Array.from(selectedIds), portfolio_id: activePortfolioId ?? "" },
      { onSuccess: () => setSelectedIds(new Set()) }
    );
  };

  const handleTaxonomyConfirm = (taxonomyIds: string[]) => {
    bulkAssignTaxonomy(
      { trade_ids: Array.from(selectedIds), taxonomy_ids: taxonomyIds },
      {
        onSuccess: () => {
          setSelectedIds(new Set());
          setShowTaxonomyPicker(false);
        },
      }
    );
  };

  const handlePlaybookConfirm = (playbookId: string | null) => {
    bulkAssignPlaybook(
      { trade_ids: Array.from(selectedIds), playbook_id: playbookId, portfolio_id: activePortfolioId ?? "" },
      {
        onSuccess: () => {
          setSelectedIds(new Set());
          setShowPlaybookPicker(false);
        },
      }
    );
  };

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Trades</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage, filter, and review your trading history.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/trades/new"
            className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground shadow hover:bg-primary/90 h-9 px-4 py-2"
          >
            <Plus className="h-4 w-4" />
            New Trade
          </Link>
        </div>
      </div>
      
      <div className="space-y-2 mt-[-8px]">
        <BulkActionToolbar
        selectedCount={selectedIds.size}
        onDelete={handleDelete}
        onAssignTaxonomy={() => setShowTaxonomyPicker(true)}
        onAssignPlaybook={() => setShowPlaybookPicker(true)}
        onMerge={selectedIds.size >= 2 ? () => setShowMergeModal(true) : undefined}
        isDeleting={isDeleting}
      />

      <TradeFilterBar
        filters={showOpenTrades ? { ...filters, status: enforcedStatus } : { ...filters, status: null }}
        onChange={handleFiltersChange}
        activeView={activeView}
        onSaveView={() => setShowSaveFilter(true)}
        onRenameView={() => setShowRenameView(true)}
        onUpdateView={handleUpdateView}
        onDeleteView={handleDeleteView}
        isUpdating={isUpdating}
        showOpenTrades={showOpenTrades}
      />

      {!showOpenTrades && openStatusBlockedHint && !bannerDismissed && (
        <div className="flex items-start justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span>
            Open trades are currently hidden, and the status filter is forced to closed. Enable 'Show Open Trades' in Settings and then open Features to show them.
          </span>
          <button
            type="button"
            onClick={() => setBannerDismissed(true)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Dismiss open-trades info banner"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <TradeTable
        portfolioId={activePortfolioId ?? undefined}
        filters={{ ...filters, status: enforcedStatus }}
        sort={sort}
        onSortChange={handleSortChange}
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        onSelectedTradesChange={setSelectedTrades}
        limit={limit}
        onLimitChange={handleLimitChange}
      />

      {showTaxonomyPicker && (
        <TaxonomyPickerModal
          onConfirm={handleTaxonomyConfirm}
          onCancel={() => setShowTaxonomyPicker(false)}
          isPending={isAssigningTaxonomy}
        />
      )}

      {showPlaybookPicker && (
        <PlaybookPickerModal
          onConfirm={handlePlaybookConfirm}
          onCancel={() => setShowPlaybookPicker(false)}
          isPending={isAssigningPlaybook}
        />
      )}

      {showMergeModal && selectedTrades.length >= 2 && (
        <MergePreviewModal
          trades={selectedTrades}
          onClose={() => setShowMergeModal(false)}
          onSuccess={(survivorId) => {
            setSelectedIds(new Set());
            setSelectedTrades([]);
            setShowMergeModal(false);
            router.push(`/dashboard/trades/${survivorId}`);
          }}
        />
      )}

      <SaveFilterModal
        isOpen={showSaveFilter}
        onClose={() => setShowSaveFilter(false)}
        currentFilters={filters}
      />

      {showRenameView && activeView && (
        <RenameViewModal
          currentName={activeView.name}
          onSave={handleRenameView}
          onClose={() => setShowRenameView(false)}
          isPending={isUpdating}
        />
      )}
    </div>
    </div>
  );
}
