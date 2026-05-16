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

interface Props {
  entityType: "all" | "trade" | "checkin";
  setEntityType: (e: "all" | "trade" | "checkin") => void;
  fromDate: string | null;
  setFromDate: (d: string | null) => void;
  toDate: string | null;
  setToDate: (d: string | null) => void;
  perPage: number;
  setPerPage: (p: number) => void;
}

export function ModelBookFilterBar({
  entityType,
  setEntityType,
  fromDate,
  setFromDate,
  toDate,
  setToDate,
  perPage,
  setPerPage,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-4 bg-card p-3 rounded-lg border border-border shadow-sm">
      <div className="flex items-center gap-1 bg-secondary rounded-md p-1 border border-border">
        {(["all", "trade", "checkin"] as const).map((type) => (
          <button
            key={type}
            onClick={() => setEntityType(type)}
            className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
              entityType === type
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-background/50"
            }`}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}s
          </button>
        ))}
      </div>
      
      <div className="h-6 w-px bg-border hidden sm:block"></div>

      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground whitespace-nowrap">From</label>
        <input
          type="date"
          value={fromDate ?? ""}
          onChange={(e) => setFromDate(e.target.value || null)}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground whitespace-nowrap">To</label>
        <input
          type="date"
          value={toDate ?? ""}
          onChange={(e) => setToDate(e.target.value || null)}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        />
      </div>
      
      <div className="flex items-center gap-2 ml-auto">
        <label className="text-sm text-muted-foreground whitespace-nowrap">Per Page</label>
        <select
          value={perPage}
          onChange={(e) => setPerPage(parseInt(e.target.value))}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        >
          <option value={12}>12</option>
          <option value={24}>24</option>
          <option value={48}>48</option>
        </select>
      </div>
    </div>
  );
}
