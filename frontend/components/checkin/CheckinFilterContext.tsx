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

import React, { createContext, useContext, useState, useEffect, useMemo } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useDebounce } from "@/hooks/useDebounce";
import type { CheckinFilterConfig } from "@/lib/api/types.gen";

export interface ExtendedCheckinFilterConfig extends CheckinFilterConfig {
  viewId: string | null;
}

interface CheckinFilterContextValue {
  filter: ExtendedCheckinFilterConfig;
  setFilter: React.Dispatch<React.SetStateAction<ExtendedCheckinFilterConfig>>;
}

const CheckinFilterContext = createContext<CheckinFilterContextValue | null>(null);

export function CheckinFilterProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Initialize from URL
  const initialFilter = useMemo<ExtendedCheckinFilterConfig>(() => {
    const hasMediaParam = searchParams.get("has_media");
    const targetIndicesParam = searchParams.get("target_indices");
    
    return {
      from_date: searchParams.get("from_date"),
      to_date: searchParams.get("to_date"),
      regime: searchParams.get("regime"),
      target_indices: targetIndicesParam ? targetIndicesParam.split(",") : null,
      has_media: hasMediaParam === "true" ? true : hasMediaParam === "false" ? false : null,
      viewId: searchParams.get("view_id"),
    };
  }, []); // Only on mount

  const [filter, setFilter] = useState<ExtendedCheckinFilterConfig>(initialFilter);
  const debouncedFilter = useDebounce(filter, 300);

  // Sync to URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    // Keep non-filter params (like view, entity_type, page, per_page)
    const view = params.get("view");
    const entityType = params.get("entity_type");
    const page = params.get("page");
    const perPage = params.get("per_page");

    // Clear all existing filter params
    params.delete("from_date");
    params.delete("to_date");
    params.delete("regime");
    params.delete("target_indices");
    params.delete("has_media");
    params.delete("view_id");

    // Re-add non-filter params if they existed
    if (view) params.set("view", view);
    if (entityType) params.set("entity_type", entityType);
    // Don't keep page param here, let it naturally reset if filters change
    if (perPage) params.set("per_page", perPage);

    // Add current filters
    if (debouncedFilter.from_date) { params.set("from_date", debouncedFilter.from_date); }
    if (debouncedFilter.to_date) { params.set("to_date", debouncedFilter.to_date); }
    if (debouncedFilter.regime) { params.set("regime", debouncedFilter.regime); }
    if (debouncedFilter.target_indices && debouncedFilter.target_indices.length > 0) { params.set("target_indices", debouncedFilter.target_indices.join(",")); }
    if (debouncedFilter.has_media !== null && debouncedFilter.has_media !== undefined) { params.set("has_media", String(debouncedFilter.has_media)); }
    if (debouncedFilter.viewId) { params.set("view_id", debouncedFilter.viewId); }

    const newSearch = params.toString();
    const currentSearch = window.location.search.replace(/^\?/, "");

    if (newSearch !== currentSearch) {
      router.replace(`${pathname}?${newSearch}`, { scroll: false });
    }
  }, [debouncedFilter, pathname, router]);

  return (
    <CheckinFilterContext.Provider value={{ filter, setFilter }}>
      {children}
    </CheckinFilterContext.Provider>
  );
}

export function useCheckinFilter() {
  const context = useContext(CheckinFilterContext);
  if (!context) throw new Error("useCheckinFilter must be used within a CheckinFilterProvider");
  return context;
}
