import { useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type { TradeFilters } from "@/hooks/useTrades";

function readFiltersFromParams(params: URLSearchParams): TradeFilters {
  const pnlRaw = params.get("pnl_positive");
  let pnl_positive: boolean | null = null;
  if (pnlRaw === "true") pnl_positive = true;
  else if (pnlRaw === "false") pnl_positive = false;

  const assetClassRaw = params.get("asset_class");
  const tagIdsRaw = params.get("tag_ids");

  const statusRaw = params.get("status");
  const status: "open" | "closed" | "all" | null =
    statusRaw === "open" || statusRaw === "closed" || statusRaw === "all" ? statusRaw : null;

  const hourRaw = params.get("hour_of_day");
  const dowRaw = params.get("day_of_week");

  return {
    symbol: params.get("symbol") ?? undefined,
    direction: params.get("direction") ?? undefined,
    asset_classes: assetClassRaw ? assetClassRaw.split(",").filter(Boolean) : undefined,
    opened_at_from: params.get("opened_at_from") ?? undefined,
    opened_at_to: params.get("opened_at_to") ?? undefined,
    closed_at_from: params.get("closed_at_from") ?? undefined,
    closed_at_to: params.get("closed_at_to") ?? undefined,
    tag_ids: tagIdsRaw ? tagIdsRaw.split(",").filter(Boolean) : undefined,
    playbook_id: params.get("playbook_id") ?? undefined,
    pnl_positive,
    status: status === "all" ? null : status,
    hour_of_day: hourRaw !== null ? parseInt(hourRaw, 10) : undefined,
    day_of_week: dowRaw !== null ? parseInt(dowRaw, 10) : undefined,
  };
}

export function useTradeFilterParams() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const savedViewId = searchParams.get("view_id");

  const filters = readFiltersFromParams(searchParams);

  const setFilter = useCallback((key: keyof TradeFilters, value: any) => {
    const params = new URLSearchParams(searchParams.toString());
    
    if (value === undefined || value === null || value === "") {
      params.delete(key);
    } else if (Array.isArray(value)) {
      if (value.length > 0) {
        params.set(key, value.join(","));
      } else {
        params.delete(key);
      }
    } else {
      params.set(key, String(value));
    }
    
    // Unset view_id when manual edits happen
    params.delete("view_id");

    // Reset pagination
    params.delete("cursor");

    router.push(`?${params.toString()}`, { scroll: false });
  }, [searchParams, router]);

  const clearFilters = useCallback(() => {
    // Keep only non-filter params if needed, or clear all
    router.push("?", { scroll: false });
  }, [router]);

  return {
    filters,
    setFilter,
    clearFilters,
    savedViewId,
  };
}
