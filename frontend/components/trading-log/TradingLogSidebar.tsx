"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, Download, Upload, TrendingUp, Lock, Filter } from "lucide-react";
import { useSavedTradeFilters } from "@/hooks/useSavedTradeFilters";
import { definitionToSearchParams } from "@/lib/tradeFilterUtils";

export function TradingLogSidebar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeViewId = searchParams.get("view_id");

  const { data: views, isLoading } = useSavedTradeFilters();

  const handleViewClick = (viewId: string, definition?: any) => {
    if (!definition) {
      // Clear filters (All Trades)
      router.push("/dashboard/trades", { scroll: false });
      return;
    }
    const params = definitionToSearchParams(definition);
    params.set("view_id", viewId);
    router.push(`/dashboard/trades?${params.toString()}`, { scroll: false });
  };

  const handleExport = () => {
    // Implement CSV export based on current filters
    const currentQuery = searchParams.toString();
    window.open(`/api/v1/trades/export?${currentQuery}`, "_blank");
  };

  const SECTION_HEADER_CLASS = "px-4 pt-4 pb-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-slate-500 select-none";
  const NAV_ITEM_CLASS = "w-full flex items-center gap-3 px-4 py-2 text-sm font-normal text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all duration-150 text-left";
  const NAV_ITEM_ACTIVE = "w-full flex items-center gap-3 px-4 py-2 text-sm font-medium nav-active transition-all duration-150 text-left";

  const renderViewItem = (id: string, name: string, definition?: any, isSystem = false) => {
    const isActive = activeViewId === id;
    return (
      <button
        key={id}
        onClick={(e) => {
          e.stopPropagation(); // prevent bubbling if needed
          handleViewClick(id, definition);
        }}
        className={`w-full flex items-center gap-2.5 py-1.5 pr-4 pl-3 text-sm font-normal rounded-md ${
          isActive
            ? "text-foreground font-medium bg-muted/40"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/20"
        } transition-all duration-150 text-left`}
      >
        <span className={`shrink-0 ${isActive ? "text-primary" : "opacity-50"}`}>
          {isSystem ? <Lock className="w-3.5 h-3.5" /> : <Filter className="w-3.5 h-3.5" />}
        </span>
        <span className="truncate flex-1">{name}</span>
      </button>
    );
  };

  const systemViews = views?.filter(v => v.scope === "SYSTEM") || [];
  const userViews = views?.filter(v => v.scope === "USER") || [];

  const isAllTradesActive = !activeViewId || activeViewId === "all";

  return (
    <div className="w-64 h-full flex flex-col bg-sidebar overflow-y-auto pb-6">
      <div className={SECTION_HEADER_CLASS}>Actions</div>
      <div className="space-y-0.5">
        <Link href="/dashboard/trades/new" className={NAV_ITEM_CLASS}>
          <Plus className="w-4 h-4 shrink-0 opacity-70" />
          <span>New Trade</span>
        </Link>
        <Link href="/dashboard/import" className={NAV_ITEM_CLASS}>
          <Upload className="w-4 h-4 shrink-0 opacity-70" />
          <span>Quick Import</span>
        </Link>
        <button onClick={handleExport} className={NAV_ITEM_CLASS}>
          <Download className="w-4 h-4 shrink-0 opacity-70" />
          <span>CSV Export</span>
        </button>
      </div>

      <div className={SECTION_HEADER_CLASS}>Saved Filters</div>
      <div className="relative">
        <button
          onClick={() => handleViewClick("all")}
          className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-all duration-150 text-left ${
            isAllTradesActive
              ? "font-medium text-foreground bg-muted/20"
              : "font-normal text-muted-foreground hover:text-foreground hover:bg-muted/20"
          }`}
        >
          <TrendingUp className={`w-4 h-4 shrink-0 ${isAllTradesActive ? "text-primary" : "opacity-70"}`} />
          <span className="truncate flex-1">All Trades</span>
        </button>

        <div className="mt-1 space-y-0.5 relative before:absolute before:left-[23px] before:top-0 before:bottom-2 before:w-px before:bg-border/60 pl-9 pr-3">
          {isLoading ? (
             <div className="py-2 pl-2 text-xs text-muted-foreground opacity-50">Loading views...</div>
          ) : (
            <>
              {systemViews.map(view => renderViewItem(view.id, view.name, view.definition, true))}
              {userViews.map(view => renderViewItem(view.id, view.name, view.definition, false))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
