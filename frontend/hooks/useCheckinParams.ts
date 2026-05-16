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

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useCallback } from "react";

export function useCheckinParams() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const view = searchParams.get("view") ?? "timeline";
  const entityType = searchParams.get("entity_type") ?? "all";
  const month = searchParams.get("month") ?? new Date().toISOString().slice(0, 7); // YYYY-MM
  const regime = searchParams.get("regime") ?? null;
  const fromDate = searchParams.get("from_date") ?? null;
  const toDate = searchParams.get("to_date") ?? null;
  
  const pageStr = searchParams.get("page");
  const page = pageStr ? parseInt(pageStr, 10) : 1;
  
  const perPageStr = searchParams.get("per_page");
  const perPage = perPageStr ? parseInt(perPageStr, 10) : 12;

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      
      if (value === null) {
        params.delete(key);
      } else {
        params.set(key, value);
      }

      // Automatically reset page to 1 if we change regime, month, or date range
      if (key === "regime" || key === "month" || key === "from_date" || key === "to_date" || key === "entity_type") {
        params.set("page", "1");
      }

      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname]
  );

  return {
    view,
    setView: (v: string) => setParam("view", v),
    entityType: entityType as "all" | "trade" | "checkin",
    setEntityType: (e: "all" | "trade" | "checkin") => setParam("entity_type", e === "all" ? null : e),
    month,
    setMonth: (m: string) => setParam("month", m),
    regime,
    setRegime: (r: string | null) => setParam("regime", r),
    fromDate,
    setFromDate: (d: string | null) => setParam("from_date", d),
    toDate,
    setToDate: (d: string | null) => setParam("to_date", d),
    page,
    setPage: (p: number) => setParam("page", p.toString()),
    perPage,
    setPerPage: (p: number) => setParam("per_page", p.toString()),
  };
}
