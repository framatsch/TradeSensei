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
 * PlaybookFilterBar — collapsible filter panel for the playbook library overview.
 */

"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Search, X } from "lucide-react";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";

export interface PlaybookFilters {
  status: "active" | "inactive" | "all";
  tagIds: string[];
  search: string;
}

export const DEFAULT_PLAYBOOK_FILTERS: PlaybookFilters = {
  status: "active",
  tagIds: [],
  search: "",
};

interface Props {
  filters: PlaybookFilters;
  onChange: (filters: PlaybookFilters) => void;
  totalCounts: {
    all: number;
    active: number;
    inactive: number;
  };
}

export function PlaybookFilterBar({ filters, onChange, totalCounts }: Props) {
  const [open, setOpen] = useState(false);
  const { data: taxonomies = [] } = useGetTaxonomies("playbook");

  // Count active non-default filters
  let activeCount = 0;
  if (filters.status !== "active") activeCount += 1;
  if (filters.tagIds.length > 0) activeCount += filters.tagIds.length;
  if (filters.search.trim().length > 0) activeCount += 1;

  const handleStatusChange = (status: "active" | "inactive" | "all") => {
    onChange({ ...filters, status });
  };

  const handleTagToggle = (tagId: string) => {
    const nextTagIds = filters.tagIds.includes(tagId)
      ? filters.tagIds.filter((id) => id !== tagId)
      : [...filters.tagIds, tagId];
    onChange({ ...filters, tagIds: nextTagIds });
  };

  const handleClearAll = () => {
    onChange(DEFAULT_PLAYBOOK_FILTERS);
  };

  return (
    <div className="solid-card shadow-sm mb-4">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setOpen((prev) => !prev)}
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors text-foreground"
            aria-expanded={open}
            aria-label="Toggle filter panel"
          >
            {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            Filter
            {activeCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground">
                {activeCount}
              </span>
            )}
          </button>

          {/* Quick status tabs */}
          <div className="flex items-center gap-1 bg-secondary/60 p-0.5 rounded-lg border border-border">
            <button
              type="button"
              onClick={() => handleStatusChange("active")}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                filters.status === "active"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Active ({totalCounts.active})
            </button>
            <button
              type="button"
              onClick={() => handleStatusChange("inactive")}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                filters.status === "inactive"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Inactive ({totalCounts.inactive})
            </button>
            <button
              type="button"
              onClick={() => handleStatusChange("all")}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                filters.status === "all"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All ({totalCounts.all})
            </button>
          </div>
        </div>

        {/* Clear all action */}
        {activeCount > 0 && (
          <button
            type="button"
            onClick={handleClearAll}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive transition-colors px-2 py-1"
          >
            <X className="w-3.5 h-3.5" />
            Clear all
          </button>
        )}
      </div>

      {/* Collapsible filter contents */}
      {open && (
        <div className="border-t border-border p-4 space-y-4 bg-muted/20">
          {/* Search field */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Search Playbooks
            </label>
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => onChange({ ...filters, search: e.target.value })}
                placeholder="Search by name or description…"
                className="w-full pl-9 pr-3 py-1.5 bg-secondary border border-border rounded-md text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {filters.search && (
                <button
                  type="button"
                  onClick={() => onChange({ ...filters, search: "" })}
                  className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Tags filter */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              Tags
            </label>
            {taxonomies.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No playbook tags available.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {taxonomies.map((tag) => {
                  const isSelected = filters.tagIds.includes(tag.id);
                  const color = tag.color_hex ?? "#888888";

                  return (
                    <button
                      key={tag.id}
                      type="button"
                      onClick={() => handleTagToggle(tag.id)}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                        isSelected
                          ? "ring-2 ring-primary ring-offset-1 ring-offset-background font-semibold"
                          : "opacity-80 hover:opacity-100"
                      }`}
                      style={{
                        backgroundColor: isSelected ? `${color}30` : `${color}15`,
                        borderColor: isSelected ? color : `${color}40`,
                        color: color,
                      }}
                    >
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      {tag.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
