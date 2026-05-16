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
 * Reporting Hub filter state — Zustand store.
 *
 * Holds the current filter configuration for the Reporting Hub dashboard.
 * The page component syncs this store with URL search params so filters
 * survive navigation and can be bookmarked.
 */

"use client";

import { create } from "zustand";

export interface ReportingFilterState {
  /** Active portfolio ID (synced from portfolioStore). */
  portfolioId: string | null;
  /** Optional inclusive start date (ISO date string). */
  dateFrom: string | null;
  /** Optional inclusive end date (ISO date string). */
  dateTo: string | null;
  /** Selected playbook IDs for filtering. */
  playbookIds: string[];
  /** Selected tag IDs for filtering. */
  tagIds: string[];
  /** When false, only closed trades are included. */
  includeOpenTrades: boolean;
  /** Active saved dashboard view ID (null = unsaved filter state). */
  viewId: string | null;

  // ── Actions ──────────────────────────────────────────────────────────────

  setPortfolioId: (id: string | null) => void;
  setDateFrom: (date: string | null) => void;
  setDateTo: (date: string | null) => void;
  setPlaybookIds: (ids: string[]) => void;
  setTagIds: (ids: string[]) => void;
  setIncludeOpenTrades: (include: boolean) => void;
  setViewId: (id: string | null) => void;

  /** Bulk-set all filter fields at once (e.g. from URL hydration). */
  setFilters: (partial: Partial<Omit<ReportingFilterState, "setFilters" | keyof ReportingFilterActions>>) => void;

  /** Reset all filters to defaults. */
  resetFilters: () => void;
}

type ReportingFilterActions = {
  setPortfolioId: ReportingFilterState["setPortfolioId"];
  setDateFrom: ReportingFilterState["setDateFrom"];
  setDateTo: ReportingFilterState["setDateTo"];
  setPlaybookIds: ReportingFilterState["setPlaybookIds"];
  setTagIds: ReportingFilterState["setTagIds"];
  setIncludeOpenTrades: ReportingFilterState["setIncludeOpenTrades"];
  setViewId: ReportingFilterState["setViewId"];
  setFilters: ReportingFilterState["setFilters"];
  resetFilters: ReportingFilterState["resetFilters"];
};

const DEFAULT_STATE = {
  portfolioId: null,
  dateFrom: null,
  dateTo: null,
  playbookIds: [] as string[],
  tagIds: [] as string[],
  includeOpenTrades: false,
  viewId: null,
};

export const useReportingFilterStore = create<ReportingFilterState>((set) => ({
  ...DEFAULT_STATE,

  setPortfolioId: (id) => set({ portfolioId: id }),
  setDateFrom: (date) => set({ dateFrom: date }),
  setDateTo: (date) => set({ dateTo: date }),
  setPlaybookIds: (ids) => set({ playbookIds: ids }),
  setTagIds: (ids) => set({ tagIds: ids }),
  setIncludeOpenTrades: (include) => set({ includeOpenTrades: include }),
  setViewId: (id) => set({ viewId: id }),

  setFilters: (partial) => set(partial),

  resetFilters: () => set({ ...DEFAULT_STATE }),
}));