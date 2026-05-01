"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Save } from "lucide-react";
import { useTradeFilterParams } from "@/hooks/useTradeFilterParams";
import type { TradeFilters } from "@/hooks/useTrades";

interface Props {
  onSaveFilter?: () => void;
}

export function FilterConfigurator({ onSaveFilter }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const { filters, setFilter } = useTradeFilterParams();

  const handleTextChange = (key: keyof TradeFilters, value: string) => {
    setFilter(key, value || undefined);
  };

  const handleStatusChange = (status: "all" | "open" | "closed") => {
    setFilter("status", status === "all" ? undefined : status);
  };

  return (
    <div className="w-full bg-card border rounded-md mb-4 shadow-sm">
      <div className="flex items-center justify-between p-3">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
        >
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          Filter Configuration
        </button>
        <button
          onClick={onSaveFilter}
          className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors px-3 py-1.5 bg-primary/10 rounded-md"
        >
          <Save className="w-3.5 h-3.5" />
          Save Filter
        </button>
      </div>

      {isOpen && (
        <div className="p-4 border-t grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Ticker / Symbol</label>
            <input
              type="text"
              value={filters.symbol || ""}
              onChange={(e) => handleTextChange("symbol", e.target.value)}
              placeholder="e.g. AAPL"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Date From</label>
            <input
              type="date"
              value={filters.opened_at_from || ""}
              onChange={(e) => handleTextChange("opened_at_from", e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Date To</label>
            <input
              type="date"
              value={filters.opened_at_to || ""}
              onChange={(e) => handleTextChange("opened_at_to", e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Trade Status</label>
            <div className="flex h-9 items-center gap-2">
              {(["all", "open", "closed"] as const).map((status) => {
                const currentStatus = filters.status || "all";
                const isActive = currentStatus === status;
                return (
                  <button
                    key={status}
                    onClick={() => handleStatusChange(status)}
                    className={`px-3 py-1 text-xs font-medium rounded-md capitalize transition-colors ${
                      isActive 
                        ? "bg-primary text-primary-foreground shadow-sm" 
                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                    }`}
                  >
                    {status}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
