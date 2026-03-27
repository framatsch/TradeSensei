import { useSavedTradeFilters, useDeleteSavedTradeFilter } from "@/hooks/useSavedTradeFilters";
import { Lock, Trash2, AlertTriangle, Eye } from "lucide-react";
import type { TradeFilters } from "@/hooks/useTrades";
import type { SavedTradeFilterRead } from "@/lib/types";

interface Props {
  onApply: (definition: Partial<TradeFilters>) => void;
  currentFilters: TradeFilters;
}

export function SavedFiltersList({ onApply, currentFilters }: Props) {
  const { data: filters, isLoading } = useSavedTradeFilters();
  const deleteFilter = useDeleteSavedTradeFilter();

  if (isLoading) {
    return <div className="p-4 text-sm text-gray-500">Loading views...</div>;
  }

  if (!filters?.length) {
    return <div className="p-4 text-sm text-gray-500">No saved views.</div>;
  }

  // Simple heuristic to check if a filter is active
  // This could be improved to check exact object equality
  const isFilterActive = (definition: Record<string, any>) => {
    const activeKeys = Object.keys(definition);
    if (activeKeys.length === 0) return false;
    
    // Check if at least some defined keys match the current filters
    return activeKeys.some(key => {
      const currentVal = (currentFilters as any)[key];
      const defVal = definition[key];
      
      if (Array.isArray(defVal) && Array.isArray(currentVal)) {
        return defVal.length === currentVal.length && 
               defVal.every(v => currentVal.includes(v));
      }
      return currentVal === defVal;
    });
  };

  return (
    <div className="space-y-1 py-2">
      {filters.map((filter) => {
        const isActive = isFilterActive(filter.definition);
        
        return (
          <div
            key={filter.id}
            className={`group flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${
              isActive 
                ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" 
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            }`}
          >
            <button
              onClick={() => onApply(filter.definition)}
              className="flex flex-1 items-center gap-2 overflow-hidden text-left"
            >
              <Eye className="h-4 w-4 shrink-0 opacity-50" />
              <span className="truncate">{filter.name}</span>
              
              {filter.scope === "SYSTEM" && (
                <Lock className="h-3 w-3 shrink-0 text-gray-400" title="System View" />
              )}
              
              {filter.needs_review && (
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" title="Needs Review" />
              )}
            </button>
            
            {filter.scope === "USER" && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("Delete this saved view?")) {
                    deleteFilter.mutate(filter.id);
                  }
                }}
                className="ml-2 hidden p-1 text-gray-400 hover:text-red-500 group-hover:block"
                title="Delete View"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
