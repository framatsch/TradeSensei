"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useDebounce } from "@/hooks/useDebounce";
import { usePortfolioStore } from "@/stores/portfolioStore";
import type { DashboardFilterConfig } from "@/lib/api/types.gen";

export interface FilterConfig extends DashboardFilterConfig {
  portfolioId: string | null;
  viewId: string | null;
  includeOpenTrades: boolean;
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

  // Read initial state from URL params
  const initialState = useMemo<FilterConfig>(() => {
    return {
      portfolioId: activePortfolioId || searchParams.get("portfolio_id") || null,
      date_from: searchParams.get("date_from") || null,
      date_to: searchParams.get("date_to") || null,
      playbook_ids: searchParams.get("playbook_ids") ? searchParams.get("playbook_ids")!.split(",") : [],
      tag_ids: searchParams.get("tag_ids") ? searchParams.get("tag_ids")!.split(",") : [],
      includeOpenTrades: searchParams.get("include_open") === "true",
      viewId: searchParams.get("view_id") || null,
    };
  }, [searchParams, activePortfolioId]);

  const [filter, setFilter] = useState<FilterConfig>(initialState);

  // Sync global portfolio ID into filter if it changes
  useEffect(() => {
    if (activePortfolioId && activePortfolioId !== filter.portfolioId) {
      setFilter(prev => ({ ...prev, portfolioId: activePortfolioId }));
    }
  }, [activePortfolioId, filter.portfolioId]);

  // Sync URL changes to internal state (e.g. clicking a saved view in the sidebar)
  useEffect(() => {
    setFilter((prev) => {
      const newState = {
        portfolioId: activePortfolioId || prev.portfolioId,
        date_from: searchParams.get("date_from") || null,
        date_to: searchParams.get("date_to") || null,
        playbook_ids: searchParams.get("playbook_ids") ? searchParams.get("playbook_ids")!.split(",") : [],
        tag_ids: searchParams.get("tag_ids") ? searchParams.get("tag_ids")!.split(",") : [],
        includeOpenTrades: searchParams.get("include_open") === "true",
        viewId: searchParams.get("view_id") || null,
      };
      
      // Only update if actually different to avoid loops
      if (JSON.stringify(prev) !== JSON.stringify(newState)) {
        return newState;
      }
      return prev;
    });
  }, [searchParams]);

  const debouncedFilter = useDebounce(filter, 300);

  // Sync internal state to URL
  useEffect(() => {
    // Construct new search string based ONLY on debouncedFilter
    const params = new URLSearchParams();
    
    // Skip portfolio_id in URL since it's managed globally via Zustand and TopBar
    if (debouncedFilter.date_from) { params.set("date_from", debouncedFilter.date_from); }
    if (debouncedFilter.date_to) { params.set("date_to", debouncedFilter.date_to); }
    if (debouncedFilter.playbook_ids && debouncedFilter.playbook_ids.length > 0) { params.set("playbook_ids", debouncedFilter.playbook_ids.join(",")); }
    if (debouncedFilter.tag_ids && debouncedFilter.tag_ids.length > 0) { params.set("tag_ids", debouncedFilter.tag_ids.join(",")); }
    if (debouncedFilter.includeOpenTrades) { params.set("include_open", "true"); }
    if (debouncedFilter.viewId) { params.set("view_id", debouncedFilter.viewId); }

    const newSearch = params.toString();
    const currentSearch = window.location.search.replace(/^\?/, ""); // Use raw window.location to avoid stale closure
    
    if (newSearch !== currentSearch) {
      router.replace(`${pathname}?${newSearch}`, { scroll: false });
    }
  }, [debouncedFilter, pathname, router]);

  return (
    <WorkspaceFilterContext.Provider value={{ filter, setFilter }}>
      {children}
    </WorkspaceFilterContext.Provider>
  );
}

export function useWorkspaceFilter() {
  const context = useContext(WorkspaceFilterContext);
  if (!context) throw new Error("useWorkspaceFilter must be used within a WorkspaceFilterProvider");
  return context;
}
