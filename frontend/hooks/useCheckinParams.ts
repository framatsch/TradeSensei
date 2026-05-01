"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useCallback } from "react";

export function useCheckinParams() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const view = searchParams.get("view") ?? "timeline";
  const month = searchParams.get("month") ?? new Date().toISOString().slice(0, 7); // YYYY-MM
  const regime = searchParams.get("regime") ?? null;
  
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

      // Automatically reset page to 1 if we change regime or month
      if (key === "regime" || key === "month") {
        params.set("page", "1");
      }

      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname]
  );

  return {
    view,
    setView: (v: string) => setParam("view", v),
    month,
    setMonth: (m: string) => setParam("month", m),
    regime,
    setRegime: (r: string | null) => setParam("regime", r),
    page,
    setPage: (p: number) => setParam("page", p.toString()),
    perPage,
    setPerPage: (p: number) => setParam("per_page", p.toString()),
  };
}
