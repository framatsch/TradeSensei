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

import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useDebounce } from "@/hooks/useDebounce";
import type { AnnotationFilterRow } from "@/components/ui/AnnotationFilterRows";

export interface CheckinFilterState {
  /** Active saved-view ID, or null if none selected. */
  viewId: string | null;
  from_date: string | null;
  to_date: string | null;
  target_indices: string[] | null;
  /** Tag (taxonomy) UUIDs to filter by (OR logic). */
  taxonomy_ids: string[] | null;
  /** Annotation filter rows. */
  annotation_filters: AnnotationFilterRow[];
  /** Display mode: timeline, gallery, etc. */
  view: string;
  /** Filter by a specific month (YYYY-MM). */
  month: string;
  /** Pagination: current page. */
  page: number;
  /** Pagination: items per page. */
  perPage: number;
}

interface CheckinFilterContextValue {
  filter: CheckinFilterState;
  setFilter: React.Dispatch<React.SetStateAction<CheckinFilterState>>;
}

const CheckinFilterContext = createContext<CheckinFilterContextValue | null>(null);

export function CheckinFilterProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Read initial state from URL params
  const computeInitialState = useCallback(() => {
    return {
      from_date: searchParams.get("from_date") || null,
      to_date: searchParams.get("to_date") || null,
      target_indices: searchParams.get("target_indices") ? searchParams.get("target_indices")!.split(",") : null,
      taxonomy_ids: searchParams.get("taxonomy_ids") ? searchParams.get("taxonomy_ids")!.split(",") : null,
      viewId: searchParams.get("view_id") || null,
      annotation_filters: [],
      view: searchParams.get("view") || "timeline",
      month: searchParams.get("month") || new Date().toISOString().slice(0, 7),
      page: searchParams.get("page") ? parseInt(searchParams.get("page")!, 10) : 1,
      perPage: searchParams.get("per_page") ? parseInt(searchParams.get("per_page")!, 10) : 12,
    };
  }, [searchParams]);

  const [filter, setFilter] = useState<CheckinFilterState>(computeInitialState);
  const [syncedSearchParams, setSyncedSearchParams] = useState(searchParams);

  // Apply URL changes before rendering children, while retaining local annotation filters.
  if (searchParams !== syncedSearchParams) {
    setSyncedSearchParams(searchParams);
    setFilter((prev) => {
      const newState: CheckinFilterState = {
        ...computeInitialState(),
        annotation_filters: prev.annotation_filters ?? [],
      };

      if (JSON.stringify(prev) !== JSON.stringify(newState)) {
        return newState;
      }
      return prev;
    });
  }

  const debouncedFilter = useDebounce(filter, 300);

  // Sync internal state to URL
  useEffect(() => {
    const params = new URLSearchParams();

    if (debouncedFilter.from_date) { params.set("from_date", debouncedFilter.from_date); }
    if (debouncedFilter.to_date) { params.set("to_date", debouncedFilter.to_date); }
    if (debouncedFilter.target_indices && debouncedFilter.target_indices.length > 0) { params.set("target_indices", debouncedFilter.target_indices.join(",")); }
    if (debouncedFilter.taxonomy_ids && debouncedFilter.taxonomy_ids.length > 0) { params.set("taxonomy_ids", debouncedFilter.taxonomy_ids.join(",")); }
    if (debouncedFilter.viewId) { params.set("view_id", debouncedFilter.viewId); }
    if (debouncedFilter.view !== "timeline") { params.set("view", debouncedFilter.view); }
    if (debouncedFilter.month !== new Date().toISOString().slice(0, 7)) { params.set("month", debouncedFilter.month); }
    if (debouncedFilter.page > 1) { params.set("page", debouncedFilter.page.toString()); }
    if (debouncedFilter.perPage !== 12) { params.set("per_page", debouncedFilter.perPage.toString()); }
    
    // Note: annotation_filters are intentionally not written to the URL to keep the URL length manageable.
    // They are stored in local state only and will be lost on hard refresh.

    const newSearch = params.toString();
    const currentSearch = window.location.search.replace(/^\?/, "");

    if (newSearch !== currentSearch) {
      router.replace(`${pathname}?${newSearch}`, { scroll: false });
    }
  }, [debouncedFilter, pathname, router]);

  const value = useMemo(() => ({ filter, setFilter }), [filter]);

  return (
    <CheckinFilterContext.Provider value={value}>
      {children}
    </CheckinFilterContext.Provider>
  );
}

export function useCheckinFilter() {
  const ctx = useContext(CheckinFilterContext);
  if (!ctx) throw new Error("useCheckinFilter must be used within a CheckinFilterProvider");
  return ctx;
}
