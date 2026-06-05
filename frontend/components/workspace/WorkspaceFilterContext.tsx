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

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useDebounce } from "@/hooks/useDebounce";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { DashboardFilterConfig, AssetClass } from "@/lib/api/types.gen";
import { useSettings } from "@/hooks/useSettings";
import { useShowOpenTrades } from "@/hooks/useShowOpenTrades";
import type { AnnotationFilterRow } from "@/components/ui/AnnotationFilterRows";

export interface FilterConfig extends DashboardFilterConfig {
  account_ids: string[];
  viewId: string | null;
  annotation_filters?: AnnotationFilterRow[];
}

interface WorkspaceFilterContextValue {
  filter: FilterConfig;
  setFilter: React.Dispatch<React.SetStateAction<FilterConfig>>;
}

const WorkspaceFilterContext = createContext<WorkspaceFilterContextValue | null>(null);

export function WorkspaceFilterProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const activePortfolioId = usePortfolioStore(s => s.activePortfolioId);
  const { isPlaceholderData: isSettingsLoading } = useSettings();
  const showOpenTrades = useShowOpenTrades();
  // Only enforce status=closed once the real settings have loaded to avoid a
  // double-query for users with show_open_trades=true (placeholder defaults to false).
  const enforceClosedStatus = !isSettingsLoading && !showOpenTrades;

  // Read initial state from URL params
  const initialState = useMemo<FilterConfig>(() => {
    return {
      date_from: searchParams.get("date_from") || null,
      date_to: searchParams.get("date_to") || null,
      playbook_ids: searchParams.get("playbook_ids") ? searchParams.get("playbook_ids")!.split(",") : [],
      taxonomy_ids: searchParams.get("taxonomy_ids") ? searchParams.get("taxonomy_ids")!.split(",") : [],
      account_ids: searchParams.get("accountIds") ? searchParams.get("accountIds")!.split(",") : [],
      symbols: searchParams.get("symbols") ? searchParams.get("symbols")!.split(",") : [],
      excluded_symbols: searchParams.get("excluded_symbols") ? searchParams.get("excluded_symbols")!.split(",") : [],
      asset_classes: searchParams.get("asset_classes") ? (searchParams.get("asset_classes")!.split(",") as AssetClass[]) : [],
      status: enforceClosedStatus
        ? "closed"
        : (searchParams.get("status") as "open" | "closed" | null) || null,
      viewId: searchParams.get("view_id") || null,
      annotation_filters: [],
    };
  }, [searchParams, enforceClosedStatus]);

  const [filter, setFilter] = useState<FilterConfig>(initialState);

  // Sync URL changes to internal state (e.g. clicking a saved view in the sidebar)
  useEffect(() => {
    setFilter((prev) => {
      const newState: FilterConfig = {
        date_from: searchParams.get("date_from") || null,
        date_to: searchParams.get("date_to") || null,
        playbook_ids: searchParams.get("playbook_ids") ? searchParams.get("playbook_ids")!.split(",") : [],
        taxonomy_ids: searchParams.get("taxonomy_ids") ? searchParams.get("taxonomy_ids")!.split(",") : [],
        account_ids: searchParams.get("accountIds") ? searchParams.get("accountIds")!.split(",") : [],
        symbols: searchParams.get("symbols") ? searchParams.get("symbols")!.split(",") : [],
        excluded_symbols: searchParams.get("excluded_symbols") ? searchParams.get("excluded_symbols")!.split(",") : [],
        asset_classes: searchParams.get("asset_classes") ? (searchParams.get("asset_classes")!.split(",") as AssetClass[]) : [],
        status: enforceClosedStatus
          ? "closed"
          : (searchParams.get("status") as "open" | "closed" | null) || null,
        viewId: searchParams.get("view_id") || null,
        annotation_filters: prev.annotation_filters ?? [],
      };

      // Only update if actually different to avoid loops
      if (JSON.stringify(prev) !== JSON.stringify(newState)) {
        return newState;
      }
      return prev;
    });
  }, [searchParams, enforceClosedStatus]);

  const debouncedFilter = useDebounce(filter, 300);

  // Sync internal state to URL
  useEffect(() => {
    const params = new URLSearchParams();

    if (debouncedFilter.date_from) { params.set("date_from", debouncedFilter.date_from); }
    if (debouncedFilter.date_to) { params.set("date_to", debouncedFilter.date_to); }
    if (debouncedFilter.playbook_ids && debouncedFilter.playbook_ids.length > 0) { params.set("playbook_ids", debouncedFilter.playbook_ids.join(",")); }
    if (debouncedFilter.taxonomy_ids && debouncedFilter.taxonomy_ids.length > 0) { params.set("taxonomy_ids", debouncedFilter.taxonomy_ids.join(",")); }
    if (debouncedFilter.account_ids && debouncedFilter.account_ids.length > 0) { params.set("accountIds", debouncedFilter.account_ids.join(",")); }
    if (debouncedFilter.symbols && debouncedFilter.symbols.length > 0) { params.set("symbols", debouncedFilter.symbols.join(",")); }
    if (debouncedFilter.excluded_symbols && debouncedFilter.excluded_symbols.length > 0) { params.set("excluded_symbols", debouncedFilter.excluded_symbols.join(",")); }
    if (debouncedFilter.asset_classes && debouncedFilter.asset_classes.length > 0) { params.set("asset_classes", debouncedFilter.asset_classes.join(",")); }
    if (enforceClosedStatus) {
      params.set("status", "closed");
    } else if (debouncedFilter.status) {
      params.set("status", debouncedFilter.status);
    }
    if (debouncedFilter.viewId) { params.set("view_id", debouncedFilter.viewId); }

    const newSearch = params.toString();
    const currentSearch = window.location.search.replace(/^\?/, "");

    if (newSearch !== currentSearch) {
      router.replace(`${pathname}?${newSearch}`, { scroll: false });
    }
  }, [debouncedFilter, pathname, router, enforceClosedStatus]);

  const value = useMemo(() => ({ filter, setFilter }), [filter]);

  return (
    <WorkspaceFilterContext.Provider value={value}>
      {children}
    </WorkspaceFilterContext.Provider>
  );
}

export function useWorkspaceFilter() {
  const context = useContext(WorkspaceFilterContext);
  if (!context) throw new Error("useWorkspaceFilter must be used within a WorkspaceFilterProvider");
  return context;
}

/**
 * Returns the active portfolio ID from the global Zustand store.
 * Use this instead of reading portfolioId from the filter state.
 */
export function useActivePortfolioId(): string | null {
  return usePortfolioStore(s => s.activePortfolioId);
}
